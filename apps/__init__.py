# -*- encoding: utf-8 -*-
import os
from flask import Flask, render_template, redirect, url_for
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from importlib import import_module
from flask_mail import Mail
from apps.database.firebase_database import firebase

db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()

def register_extensions(app):
    db.init_app(app)
    login_manager.init_app(app)

def register_blueprints(app):
    for module_name in ('authentication', 'home'):
        module = import_module('apps.{}.routes'.format(module_name))
        app.register_blueprint(module.blueprint)

from apps.authentication.oauth import github_blueprint, google_blueprint
from apps.users.routes import users_blueprint
from apps.api.routes import api_blueprint


def create_app(config):

    # Contextual
    static_prefix = '/static'
    templates_dir = os.path.dirname(config.BASE_DIR)

    TEMPLATES_FOLDER = os.path.join(templates_dir,'templates')
    STATIC_FOLDER = os.path.join(templates_dir,'static')

    print(' > TEMPLATES_FOLDER: ' + TEMPLATES_FOLDER)
    print(' > STATIC_FOLDER:    ' + STATIC_FOLDER)

    app = Flask(__name__, static_url_path=static_prefix, template_folder=TEMPLATES_FOLDER, static_folder=STATIC_FOLDER)

    app.config.from_object(config)
    mail.init_app(app)
    register_extensions(app)
    register_blueprints(app)
    app.register_blueprint(github_blueprint, url_prefix="/login")    
    app.register_blueprint(google_blueprint, url_prefix="/login")    
    app.register_blueprint(users_blueprint)
    app.register_blueprint(api_blueprint)

    @app.context_processor
    def inject_kelas_list():
        return {
            "kelas_list": sorted(firebase.class_list())
        }

        # --- error handlers (global) ---
    
    @login_manager.unauthorized_handler
    def unauthorized():
        return redirect('/login')

    @app.errorhandler(401)
    def handle_401(error):
        return redirect('/login')


    @app.errorhandler(403)
    def handle_403(error):
        return render_template("error/403.html"), 403

    @app.errorhandler(404)
    def handle_404(error):
        return render_template("error/404.html"), 404
    
    @app.errorhandler(405)
    def handle_405(error):
        return render_template("error/405.html"), 405

    @app.errorhandler(500)
    def handle_500(error):
        return render_template("error/500.html"), 500
    
    return app
