from flask import Flask, request, make_response
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
    
    # ✅ UPDATED: Define allowed origins including your current frontend domain
    ALLOWED_ORIGINS = [
        'https://pes-park.vercel.app',        # Previous domain
        'https://smart-carpark.vercel.app',   # ✅ ADDED: Current domain
        'http://localhost:3000',              # Local development
        'http://localhost:5173',              # ✅ ADDED: Vite default port
        'http://127.0.0.1:5173',             # ✅ ADDED: Alternative local
    ]
    
    # Manual CORS handler for ALL requests
    @app.before_request
    def handle_cors():
        origin = request.headers.get('Origin')
        
        # Log all requests with better formatting
        print(f"🌐 REQUEST: {request.method} {request.path} from {origin}")
        
        # Handle preflight OPTIONS requests
        if request.method == "OPTIONS":
            response = make_response()
            
            # ✅ MODIFIED: Always allow CORS for any origin (including hardware with no origin)
            if origin and origin in ALLOWED_ORIGINS:
                response.headers['Access-Control-Allow-Origin'] = origin
                print(f"✅ CORS ALLOWED: {origin}")
            else:
                # ✅ CHANGED: Allow all origins (including null/no origin for hardware)
                response.headers['Access-Control-Allow-Origin'] = '*'
                print(f"✅ CORS ALLOWED: All origins (hardware friendly)")
                
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Accept, Origin, X-Requested-With'
            response.headers['Access-Control-Max-Age'] = '3600'
            response.headers['Access-Control-Allow-Credentials'] = 'false'
            
            print(f"✅ PREFLIGHT RESPONSE: {response.headers.get('Access-Control-Allow-Origin')}")
            return response, 200
    
    # Add CORS headers to all actual responses
    @app.after_request  
    def add_cors_headers(response):
        origin = request.headers.get('Origin')
        
        # ✅ MODIFIED: Always add permissive CORS headers
        if origin and origin in ALLOWED_ORIGINS:
            response.headers['Access-Control-Allow-Origin'] = origin
            print(f"✅ CORS HEADERS ADDED: {origin}")
        else:
            # ✅ CHANGED: Allow all origins (hardware friendly)
            response.headers['Access-Control-Allow-Origin'] = '*'
            print(f"✅ CORS HEADERS ADDED: All origins allowed")
            
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Accept, Origin, X-Requested-With'
        
        print(f"📤 RESPONSE: {request.method} {request.path} -> {response.status}")
        return response
    
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
    
    # Root endpoint - Updated to show hardware support
    @app.route('/')
    def root():
        return {
            'message': 'Parking API is running',
            'status': 'healthy',
            'service': 'parking-api',
            'version': '1.0',
            'cors': 'permissive',  # ✅ UPDATED
            'hardware_requests': 'allowed',  # ✅ ADDED
            'allowed_origins': ALLOWED_ORIGINS,
        }, 200
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        return {
            'status': 'healthy', 
            'service': 'parking-api',
            'hardware_requests': 'allowed',  # ✅ ADDED
            'allowed_origins': ALLOWED_ORIGINS
        }, 200

    return app

app = create_app()

if __name__ == '__main__':
    app.run(
        debug=app.config.get('DEBUG', False),
        host=app.config.get('HOST', '0.0.0.0'),
        port=app.config.get('PORT', 5000)
    )