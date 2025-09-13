import os

# Get the absolute path of the directory where this file is located
basedir = os.path.abspath(os.path.dirname(__file__))

class Config():
    DEBUG = False
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
   
    CELERY = dict(
        broker_url="redis://localhost:6379/0",
        result_backend="redis://localhost:6379/0",
        broker_connection_retry_on_startup=True,
        
        include=["application.tasks"]
    )
    
class LocalDevelopmentConfig(Config):
    
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(basedir, "db_directory", "testdb.sqlite3")
    DEBUG = True
    
    # Other Flask and extension settings
    UPLOAD_FOLDER = 'uploads/'
    CACHE_TYPE = 'RedisCache'
    CACHE_REDIS_URL = 'redis://localhost:6379/0'
    SECRET_KEY = "Secret is meant to be Secret"
    JWT_SECRET_KEY = 'your_jwt_secret_key'