from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional, Regexp, ValidationError
from app import db
from app.models.user import User
from app.utils.images import validate_image_upload


class SignupForm(FlaskForm):
    username = StringField(
        'Username',
        validators=[
            DataRequired(),
            Length(min=3, max=80),
            Regexp(r'^[A-Za-z0-9_]+$', message='Letters, numbers, and underscores only.'),
        ],
    )
    email = StringField(
        'Email',
        validators=[DataRequired(), Email(), Length(max=120)],
    )
    password = PasswordField(
        'Password',
        validators=[DataRequired(), Length(min=8, max=128)],
    )
    confirm_password = PasswordField(
        'Confirm password',
        validators=[DataRequired(), EqualTo('password', message='Passwords do not match.')],
    )
    submit = SubmitField('Sign Up')

    def validate_username(self, field):
        existing = db.session.execute(
            db.select(User).where(db.func.lower(User.username) == field.data.lower())
        ).scalar_one_or_none()
        if existing:
            raise ValidationError('This username is already taken.')

    def validate_email(self, field):
        existing = db.session.execute(
            db.select(User).where(User.email == field.data.lower())
        ).scalar_one_or_none()
        if existing:
            raise ValidationError('This email is already registered.')


class LoginForm(FlaskForm):
    email = StringField(
        'Email',
        validators=[DataRequired(), Email(), Length(max=120)],
    )
    password = PasswordField(
        'Password',
        validators=[DataRequired()],
    )
    submit = SubmitField('Log In')


class LogoutForm(FlaskForm):
    submit = SubmitField('Logout')


MAX_AVATAR_BYTES = 2 * 1024 * 1024
ALLOWED_AVATAR_TYPES = {'jpeg', 'png', 'webp'}


class ProfileForm(FlaskForm):
    username = StringField(
        'Username',
        validators=[
            DataRequired(),
            Length(min=3, max=80),
            Regexp(r'^[A-Za-z0-9_]+$', message='Letters, numbers, and underscores only.'),
        ],
    )
    email = StringField(
        'Email',
        validators=[DataRequired(), Email(), Length(max=120)],
    )
    current_password = PasswordField(
        'Current password',
        validators=[Optional(), Length(max=128)],
    )
    new_password = PasswordField(
        'New password',
        validators=[Optional(), Length(min=8, max=128)],
    )
    confirm_new_password = PasswordField(
        'Confirm new password',
        validators=[Optional(), EqualTo('new_password', message='Passwords do not match.')],
    )
    avatar = FileField('Profile picture')
    submit = SubmitField('Save changes')

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._user = user

    def validate_username(self, field):
        existing = db.session.execute(
            db.select(User).where(
                db.func.lower(User.username) == field.data.lower(),
                User.id != self._user.id,
            )
        ).scalar_one_or_none()
        if existing:
            raise ValidationError('This username is already taken.')

    def validate_email(self, field):
        existing = db.session.execute(
            db.select(User).where(
                User.email == field.data.lower(),
                User.id != self._user.id,
            )
        ).scalar_one_or_none()
        if existing:
            raise ValidationError('This email is already registered.')

    def validate_current_password(self, field):
        if not self.new_password.data:
            return
        if not field.data:
            raise ValidationError('Enter your current password to change it.')
        if not self._user.check_password(field.data):
            raise ValidationError('Current password is incorrect.')

    def validate_avatar(self, field):
        validate_image_upload(
            field.data,
            max_bytes=MAX_AVATAR_BYTES,
            allowed_types=ALLOWED_AVATAR_TYPES,
            oversize_message='Picture must be 2 MB or smaller.',
            invalid_message='Please upload a PNG, JPG or WEBP image.',
        )
