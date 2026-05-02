from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Regexp, ValidationError
from app.extensions import db
from app.models.user import User


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
