"""Flask-Login wiring. Single-user MVP, but the User table supports many."""
from flask_login import UserMixin, LoginManager
from werkzeug.security import generate_password_hash, check_password_hash

import db

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.login_message = "Sign in to continue."


class User(UserMixin):
    def __init__(self, row):
        self.id = row["id"]
        self.username = row["username"]
        self.password_hash = row["password_hash"]
        self.email = row["email"]

    @staticmethod
    def by_id(user_id):
        row = db.query_one("SELECT * FROM users WHERE id = ?", (user_id,))
        return User(row) if row else None

    @staticmethod
    def by_username(username):
        row = db.query_one("SELECT * FROM users WHERE username = ?", (username,))
        return User(row) if row else None

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


def create_user(username, password, email=None):
    if User.by_username(username):
        raise ValueError(f"User {username!r} already exists")
    password_hash = generate_password_hash(password)
    return db.execute(
        "INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)",
        (username, password_hash, email),
    )


@login_manager.user_loader
def load_user(user_id):
    try:
        return User.by_id(int(user_id))
    except (TypeError, ValueError):
        return None
