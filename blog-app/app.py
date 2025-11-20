from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

# ----------------------------
# Config & app init
# ----------------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = 'replace-this-with-a-secure-random-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'  # redirects to login for @login_required

# ----------------------------
# Models
# ----------------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    posts = db.relationship('Post', backref='author', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# ----------------------------
# Login loader
# ----------------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ----------------------------
# DB init helper
# ----------------------------
# ----------------------------
# DB init helper (safe: uses app context)
# ----------------------------
def init_db():
    """
    Create the DB tables inside an application context.
    If blog.db already exists, this will not overwrite it.
    """
    with app.app_context():
        if not os.path.exists('blog.db'):
            db.create_all()
            print("Created blog.db and tables")


init_db()

# ----------------------------
# Routes - Public
# ----------------------------
@app.route('/')
def index():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('index.html', posts=posts)

@app.route('/post/<int:post_id>')
def view_post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post.html', post=post)

# ----------------------------
# Routes - Auth
# ----------------------------
@app.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not email or not password:
            flash('All fields are required.', 'danger')
            return redirect(url_for('register'))

        if User.query.filter((User.username==username) | (User.email==email)).first():
            flash('Username or email already exists.', 'danger')
            return redirect(url_for('register'))

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username_or_email = request.form.get('username_or_email', '').strip()
        password = request.form.get('password', '').strip()

        user = User.query.filter((User.username==username_or_email) | (User.email==username_or_email)).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully.', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        flash('Invalid credentials.', 'danger')
        return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out.', 'info')
    return redirect(url_for('index'))

# ----------------------------
# Routes - Post operations (requires login)
# ----------------------------
@app.route('/create', methods=('GET', 'POST'))
@login_required
def create_post():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        body = request.form.get('body', '').strip()
        if not title:
            flash('Title is required.', 'danger')
            return redirect(url_for('create_post'))
        post = Post(title=title, body=body, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Post created.', 'success')
        return redirect(url_for('index'))
    return render_template('create_post.html')

@app.route('/edit/<int:post_id>', methods=('GET', 'POST'))
@login_required
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    # allow only author to edit
    if post.author != current_user:
        abort(403)

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        body = request.form.get('body', '').strip()
        if not title:
            flash('Title required.', 'danger')
            return redirect(url_for('edit_post', post_id=post_id))
        post.title = title
        post.body = body
        db.session.commit()
        flash('Post updated.', 'success')
        return redirect(url_for('view_post', post_id=post.id))
    return render_template('edit_post.html', post=post)

@app.route('/delete/<int:post_id>', methods=('POST',))
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Post deleted.', 'info')
    return redirect(url_for('index'))

# ----------------------------
# Run app
# ----------------------------
if __name__ == '__main__':
    app.run(debug=True)
