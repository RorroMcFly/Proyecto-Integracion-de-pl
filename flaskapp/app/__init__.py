# app/__init__.py
from flask import Flask
from flask_jwt_extended import JWTManager
from .routes import routes_bp

def create_app():
    app = Flask(__name__)
    
    # Cargar configuraciones desde la clase Config
    app.config.from_object('instance.config.Config')
    
    jwt = JWTManager(app)  # Inicializa JWT Manager con la app configurada
    
    app.register_blueprint(routes_bp)

    return app
