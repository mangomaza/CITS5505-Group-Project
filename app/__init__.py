import os
from flask import Flask, render_template
from config import config
from app.extensions import db, migrate, login_manager


def create_app(config_name='default'):
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'),
        static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static'),
    )

    app.config.from_object(config[config_name])

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    from app.models import User
    from app.forms.auth_forms import LogoutForm

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.context_processor
    def inject_logout_form():
        return {'logout_form': LogoutForm()}

    from app.routes.main_routes import main_bp
    from app.routes.auth_routes import auth_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    return app
