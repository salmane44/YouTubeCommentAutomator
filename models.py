from app import db
from flask_login import UserMixin
from datetime import datetime

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    oauth_provider = db.Column(db.String(20), default='google')  # For future OAuth providers
    oauth_id = db.Column(db.String(100), nullable=True)  # Store Google user ID
    is_verified = db.Column(db.Boolean, default=True)  # Google users are pre-verified
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    youtube_channels = db.relationship('YouTubeChannel', backref='user', lazy=True)
    settings = db.relationship('UserSettings', backref='user', uselist=False, lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'

class YouTubeChannel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    channel_id = db.Column(db.String(100), unique=True, nullable=False)
    channel_name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    verification_code = db.Column(db.String(10), nullable=True)
    verification_code_expiry = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    comments = db.relationship('CommentHistory', backref='channel', lazy=True)

    def __repr__(self):
        return f'<YouTubeChannel {self.channel_name}>'

class UserSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    auto_reply_enabled = db.Column(db.Boolean, default=True)
    custom_prompt = db.Column(db.Text, nullable=True)
    reply_delay = db.Column(db.Integer, default=0)  # Delay in seconds
    reply_time_window = db.Column(db.Integer, default=7)  # Days
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<UserSettings for user {self.user_id}>'

class CommentHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    channel_id = db.Column(db.Integer, db.ForeignKey('you_tube_channel.id'), nullable=False)
    comment_id = db.Column(db.String(100), nullable=False, unique=True)
    video_id = db.Column(db.String(100), nullable=False)
    comment_text = db.Column(db.Text, nullable=False)
    author_name = db.Column(db.String(100), nullable=False)
    author_id = db.Column(db.String(100), nullable=False)
    published_at = db.Column(db.DateTime, nullable=False)
    replied = db.Column(db.Boolean, default=False)
    reply_text = db.Column(db.Text, nullable=True)
    replied_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Moderation fields
    moderation_status = db.Column(db.String(20), default="pending", nullable=True)  # pending, approved, rejected, flagged
    moderation_notes = db.Column(db.Text, nullable=True)
    moderated_at = db.Column(db.DateTime, nullable=True)
    is_selected = db.Column(db.Boolean, default=False)  # For bulk selection

    def __repr__(self):
        return f'<CommentHistory for comment {self.comment_id}>'

class VerificationCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    channel_id = db.Column(db.Integer, db.ForeignKey('you_tube_channel.id'), nullable=False)
    code = db.Column(db.String(10), nullable=False)
    expiry = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<VerificationCode for channel {self.channel_id}>'