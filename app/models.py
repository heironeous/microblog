from __future__ import annotations
from datetime import datetime
from hashlib import md5
from flask_login import UserMixin
from app import db, login
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy.query import Query

@login.user_loader
def load_user(id):
    return User.query.get(int(id))


followers = db.Table('followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    about_me = db.Column(db.String(140))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    
    followed = db.relationship(
        'User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')
    
    def avatar(self, size: str) -> str:
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(
            digest, size)

    def __repr__(self) -> str:
        return '<User {}>'.format(self.username)
    
    def __eq__(self, other: User) -> bool:
        return ((self.username, self.email.lower()) ==
                (other.username, other.email.lower()))
    
    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)
    
    def follow(self, user: User) -> None:
        if not self.is_following(user) and self != user:
            self.followed.append(user)
    
    def unfollow(self, user: User) -> None:
        if self.is_following(user) and self != user:
            self.followed.remove(user)
            
    def is_following(self, user: User) -> bool:
        return self.followed.filter(
            followers.c.followed_id == user.id).count() > 0
        
    def my_posts(self) -> Query:
        return Post.query.filter_by(user_id=self.id)
        
    def followed_posts(self) -> Query:
        return Post.query.join(
            followers, (followers.c.followed_id == Post.user_id)).filter(
                followers.c.follower_id == self.id)
                
    def all_posts(self) -> Query:
        myposts = self.my_posts()
        followedposts = self.followed_posts()
        return followedposts.union(myposts).order_by(Post.timestamp.desc())
    
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return '<Post {} created at {}>'.format(self.body, self.timestamp)
