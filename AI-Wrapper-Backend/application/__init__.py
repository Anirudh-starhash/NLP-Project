import os
from flask import Flask, jsonify, send_from_directory
from flask_restful import Api
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_caching import Cache
from celery import Celery, Task

from .database import db
from .config import LocalDevelopmentConfig

# 1. Create extension instances OUTSIDE the factory
celery = Celery(__name__)
migrate = Migrate()
jwt = JWTManager()
cache = Cache()
cors = CORS()

def create_app():
    app = Flask(__name__)
    app.config.from_object(LocalDevelopmentConfig)
    
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # 2. Initialize all extensions INSIDE the factory
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cache.init_app(app)
    cors.init_app(app, 
                  resources={r"/api/*": {"origins": "http://localhost:4200"}}, 
                  supports_credentials=True)
    api = Api(app)
    
    # Push app context before setting up Celery and blueprints
    app.app_context().push()

    # 3. Configure Celery
    celery.conf.update(app.config)

    class ContextTask(Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask

    # 4. Define all your routes and error handlers INSIDE the factory
    @app.route("/")
    def home():
        return jsonify({'msg':'Hey you are connected to backend!'}), 200
    
    @app.route('/uploads/<path:filename>')
    def serve_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    @app.route("/cache")
    @cache.cached(timeout=30)
    def index():
        return jsonify({'msg':'Cache is Working'}), 200

    @app.errorhandler(404)
    def page_not_found(e):
        return jsonify({'msg':'Page Not found'}), 404
    
    @app.errorhandler(401)
    def not_authorized(e):
        return jsonify({'msg':'Not Authorized'}), 401
    
    # 5. Import and register blueprints
    from .user_controllers import user_blueprint
    from .file_controllers import file_blueprint
    app.register_blueprint(user_blueprint, url_prefix='/api')
    app.register_blueprint(file_blueprint, url_prefix='/api')
    
    return app, api, celery

app, api, celery_instance = create_app()