print("STARTING APP.PY")
import os
from flask import Flask
from dotenv import load_dotenv
print("IMPORTED DOTENV")
from flask_login import LoginManager
from flask_cors import CORS
from db import init_driver, close_driver, get_driver
print("IMPORTED DB")
from routes import bp as routes_bp
from auth import bp as auth_bp
print("DONE IMPORTS")

# Load `.env` from backend directory
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))


def create_app():
    print("CREATING APP")
    app = Flask(__name__)
    app.secret_key = "super-secret-key-change-this-in-prod" # Required for session
    # Enable CORS for frontend - accepts all localhost origins
    CORS(app, resources={r"/*": {
        "origins": [
            "http://localhost:8080", "http://127.0.0.1:8080",
            "http://localhost:8081", "http://127.0.0.1:8081",
            "http://localhost:5500", "http://127.0.0.1:5500",
            "http://localhost:3000", "http://127.0.0.1:3000",
            "http://localhost:4200", "http://127.0.0.1:4200",
            "http://localhost",     "http://127.0.0.1",
            "null"  # file:// pages
        ],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
        "supports_credentials": True
    }}, supports_credentials=True)
    
    init_driver()
    
    login_manager = LoginManager()
    login_manager.init_app(app)
    
    @login_manager.unauthorized_handler
    def unauthorized():
        from flask import jsonify
        return jsonify({"error": "Non authentifié", "authenticated": False}), 401
    
    @login_manager.user_loader
    def load_user(user_id):
        driver = get_driver()
        return driver.get_user(user_id) if driver else None
    
    app.register_blueprint(routes_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")

    # @app.teardown_appcontext
    # def shutdown(exception=None):
    #     close_driver()

    return app


if __name__ == "__main__":
    print("ENTERING MAIN")
    app = create_app()
    port = int(os.getenv("FLASK_RUN_PORT", 5001))
    print("MAPPING URLS:")
    try:
        with open("url_map.txt", "w") as f: f.write(str(app.url_map))
    except: pass
    app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)
