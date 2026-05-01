from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.extensions import db
from app.models.user import User

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    field_errors = {}

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not username:
            field_errors['username'] = 'Username is required.'

        if not email:
            field_errors['email'] = 'Email is required.'

        if len(password) < 8:
            field_errors['password'] = 'Password must be at least 8 characters.'

        if password != confirm_password:
            field_errors['confirm_password'] = 'Passwords do not match.'

        if username and User.query.filter_by(username=username).first():
            field_errors['username'] = 'This username is already taken.'

        if email and User.query.filter_by(email=email).first():
            field_errors['email'] = 'This email is already registered.'

        if field_errors:
            return render_template(
                'signup.html',
                field_errors=field_errors,
                username=username,
                email=email
            )

        user = User(username=username, email=email)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        session['user_id'] = user.id
        session['username'] = user.username

        flash(f'Welcome, {user.username}!', 'success')
        return redirect('/')

    return render_template('signup.html', field_errors={})


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username

            flash(f'Welcome back, {user.username}!', 'success')
            return redirect('/')

        flash('Invalid email or password.', 'danger')
        return render_template('login.html', email=email)

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    if 'user_id' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('auth.login'))

    session.clear()
    flash('You have been logged out.', 'success')
    return redirect('/')