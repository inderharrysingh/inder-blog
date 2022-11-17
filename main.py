from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, Register, Login_form, Comment
from flask_gravatar import Gravatar
import os
app = Flask(__name__)

app.config['SECRET_KEY'] = "8BYkEfBA6O6donzWlSihBXox7C0sKR6b"

ckeditor = CKEditor(app)
Bootstrap(app)
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

##CONNECT TO DB
##if sqlite:///blog.db\8BYkEfBA6O6donzWlSihBXox7C0sKR6b
if os.environ.get('DATABASE_URL') != None:
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')

else:
   app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///blog.db"

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# CONFIGURING THE LOGIN MANAGER TO WORK WITH OUR FLASK APP
login_manager = LoginManager()
login_manager.init_app(app)

##CONFIGURE TABLES
with app.app_context():
    class Users(db.Model, UserMixin):
        __tablename__ = "users"
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(250))
        email = db.Column(db.String(500), nullable=False, unique=True)
        password = db.Column(db.String(1000), nullable=False)

        # with this key word posts_id we can access all the posts that our user has so for typed
        posts = relationship('BlogPost', back_populates='author')
        comments = relationship("view", back_populates='author')


    class BlogPost(db.Model):
        __tablename__ = "blog_posts"
        id = db.Column(db.Integer, primary_key=True)

        title = db.Column(db.String(250), unique=True, nullable=False)
        subtitle = db.Column(db.String(250), nullable=False)
        date = db.Column(db.String(250), nullable=False)
        body = db.Column(db.Text, nullable=False)
        img_url = db.Column(db.String(250), nullable=False)
        author = relationship("Users", back_populates="posts")
        # creating new column in blog post which will store the id of the users who had created  that particular blog because we have explicityl mentioned users.id
        # if we want to store something else associated with the users we can also do that
        author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
        comments = relationship("view", back_populates='parent_post')

        # at the time of intialising, we have to pass on the instance of users class as the argument ot  post parameter that we have created in the parent class


    class view(db.Model):
        __tablename__ = "comment"
        id = db.Column(db.Integer, primary_key=True)
        text = db.Column(db.String(10000))
        author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
        author = relationship("Users", back_populates='comments')
        parent_post = relationship("BlogPost", back_populates='comments')
        post_id = db.Column(db.Integer, db.ForeignKey('blog_posts.id'))


# LOGGING USER IN
@login_manager.user_loader
def load_user(id):
    return Users.query.get(id)


# MAKING ONLY ADMIN ACCESS PRIVATE ROUTE
from functools import wraps
from flask import g, request, redirect, url_for


def only_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.id != 1:
            return abort(403,
                         "You don't have access to use this end point, if your are the developer login with the admin account")
        return f(*args, **kwargs)

    return decorated_function


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts)


@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        with app.app_context():
            email = request.form.get('name')

            row = Users.query.filter_by(email=email).first()

            if row != None:
                flash("This email is already registered, try to login instead ")
                return redirect('/login')

            new_user = Users(name=request.form.get('name'),
                             email=request.form.get('email'),
                             password=generate_password_hash(request.form.get('password')
                                                             , method="pbkdf2:sha256",
                                                             salt_length=8))
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect('/login')

    form = Register()
    return render_template("register.html", form=form)


@app.route('/login', methods=["POST", "GET"])
def login():
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')
        with app.app_context():
            row = Users.query.filter_by(email=email).first()
            if row == None:
                flash('this email is not registered, please register first')
                return redirect('/register')
            if not check_password_hash(row.password, password):
                flash("Invalid password, please try agian")
                return redirect('/login')

            login_user(row)
            return redirect('/')

    form = Login_form()
    return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
@login_required
def show_post(post_id):
    comment = Comment()
    if request.method == "POST":
        with app.app_context():
            new_comment = view(
                text=comment.comment.data,
                author_id=current_user.id,
                post_id=post_id
            )
            print(request.form.get('body'))
            db.session.add(new_comment)
            db.session.commit()

            return redirect(url_for('show_post', post_id=post_id))

    requested_post = BlogPost.query.get(post_id)

    with app.app_context():
        rows = db.session.query(view).all()
        for i in rows:
            print(i.author.name)
            print(i.author.email)
    return render_template("post.html", post=requested_post, form=comment, data=rows, id=post_id)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/new-post", methods=["GET", "POST"])
@only_admin
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        with app.app_context():
            new_post = BlogPost(
                title=form.title.data,
                subtitle=form.subtitle.data,
                body=form.body.data,
                img_url=form.img_url.data,
                author=current_user,
                date=date.today().strftime("%B %d, %Y")
            )
            db.session.add(new_post)
            db.session.commit()
            return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>")
@only_admin
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        with app.app_context():
            post.title = edit_form.title.data
            post.subtitle = edit_form.subtitle.data
            post.img_url = edit_form.img_url.data
            post.author = edit_form.author.data
            post.body = edit_form.body.data
            db.session.commit()
            return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
@only_admin
def delete_post(post_id):
    with app.app_context():
        post_to_delete = BlogPost.query.get(post_id)
        db.session.delete(post_to_delete)
        db.session.commit()
        return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
