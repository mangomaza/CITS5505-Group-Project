import os
from flask import Flask
from config import config
from app.extensions import db, migrate


def create_app(config_name='default'):
    app = Flask(__name__,
                template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'),
                static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static'))

    app.config.from_object(config[config_name])

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)

    from app.routes.main_routes import main_bp
    from app.routes.auth_routes import auth_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)

    return app
