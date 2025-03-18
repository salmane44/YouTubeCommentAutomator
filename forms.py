from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, IntegerField, DateField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, Optional, NumberRange
from models import User

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    password_confirm = PasswordField('Confirm Password', 
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')
            
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class AddYouTubeChannelForm(FlaskForm):
    channel_id = StringField('YouTube Channel ID', validators=[DataRequired()])
    submit = SubmitField('Add Channel')

class VerifyChannelForm(FlaskForm):
    verification_code = StringField('Verification Code', validators=[DataRequired(), Length(min=6, max=6)])
    submit = SubmitField('Verify Channel')

class SettingsForm(FlaskForm):
    auto_reply_enabled = BooleanField('Enable Auto Reply')
    custom_prompt = TextAreaField('Custom Prompt Template', validators=[Optional()])
    reply_delay = IntegerField('Reply Delay (seconds)', validators=[Optional(), NumberRange(min=0, max=3600)])
    reply_time_window = IntegerField('Reply Time Window (days)', validators=[Optional(), NumberRange(min=1, max=30)])
    submit = SubmitField('Save Settings')

class CommentFilterForm(FlaskForm):
    start_date = DateField('Start Date', validators=[Optional()], format='%Y-%m-%d')
    end_date = DateField('End Date', validators=[Optional()], format='%Y-%m-%d')
    submit = SubmitField('Filter Comments')
    
class BulkModerationForm(FlaskForm):
    moderation_status = SelectField('Status', choices=[
        ('approved', 'Approve'),
        ('rejected', 'Reject'),
        ('flagged', 'Flag for Review')
    ])
    moderation_notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Apply to Selected')
    
class CommentReplyForm(FlaskForm):
    reply_text = TextAreaField('Reply', validators=[DataRequired()])
    submit = SubmitField('Send Reply')
