from flask import Flask
from flask_cors import CORS
from config import Config
from services.firebase_service import FirebaseService
from routes.auth_routes import auth_bp
from routes.booking_routes import booking_bp
from routes.payment_routes import payment_bp
from routes.parking_routes import parking_bp
from middleware.error_handlers import register_error_handlers
from middleware.logging_middleware import setup_logging
import logging

def create_app():
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(Config)
    
    # Enable CORS
    CORS(app, origins=app.config.get('ALLOWED_ORIGINS', ['*']))
    
    # Setup logging
    setup_logging(app)
    
    # Initialize Firebase
    firebase_service = FirebaseService()
    firebase_service.initialize()
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(booking_bp, url_prefix='/booking')
    app.register_blueprint(payment_bp, url_prefix='/payment')
    app.register_blueprint(parking_bp, url_prefix='/parking')
    
    # Register error handlers
    register_error_handlers(app)
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        return {'status': 'healthy', 'service': 'parking-api'}, 200
    
    return app

# Create the app at module level for Gunicorn
app = create_app()

if __name__ == '__main__':
    app.run(
        debug=app.config.get('DEBUG', False),
        host=app.config.get('HOST', '0.0.0.0'),
        port=app.config.get('PORT', 5000)
    )