import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from dotenv import load_dotenv

# ─── 1) Load environment variables ─────────────────────────────────────────────
print("Loading environment variables...")
load_dotenv()

required_vars = ['DATABASE_URL', 'SECRET_KEY', 'MAIL_SERVER', 'MAIL_USERNAME', 'MAIL_PASSWORD']
missing = [v for v in required_vars if not os.getenv(v)]
if missing:
    print(f"ERROR: Missing required env vars: {missing}")
    sys.exit(1)

# ─── 2) Initialize extensions ─────────────────────────────────────────────────
db            = SQLAlchemy()
migrate       = Migrate()
login_manager = LoginManager()
mail          = Mail()

login_manager.login_view = 'auth.login'


def create_app():
    print("Creating Flask application...")
    app = Flask(__name__)

    # ─── 3) Core config from .env ───────────────────────────────────────────────
    app.config['SECRET_KEY']            = os.getenv('SECRET_KEY')
    database_url                        = os.getenv('DATABASE_URL')
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
        print("Converted postgres:// → postgresql:// in DATABASE_URL")
    app.config['SQLALCHEMY_DATABASE_URI']       = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ECHO']               = False  # set True for debug
    app.config['SQLALCHEMY_ENGINE_OPTIONS']     = {
        'pool_pre_ping': True,
        'pool_recycle': 3600,
        'connect_args': { 'connect_timeout': 10 }
    }

    # ─── 4) Mail config from .env ───────────────────────────────────────────────
    app.config['MAIL_SERVER']         = os.getenv('MAIL_SERVER')
    app.config['MAIL_PORT']           = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS']        = os.getenv('MAIL_USE_TLS', 'True').lower() in ('true', '1', 'yes')
    app.config['MAIL_USE_SSL']        = os.getenv('MAIL_USE_SSL', 'False').lower() in ('true', '1', 'yes')
    app.config['MAIL_USERNAME']       = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD']       = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

    # ─── 5) Initialize extensions ────────────────────────────────────────────────
    print("Initializing Flask extensions...")
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)

    # ─── 6) Register blueprints ──────────────────────────────────────────────────
    print("Registering blueprints...")
    from app.controllers.main      import main_bp
    from app.controllers.auth      import auth_bp
    from app.controllers.inventory import inventory_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp,      url_prefix='/auth')
    app.register_blueprint(inventory_bp, url_prefix='/inventory')

    # ─── 7) Create DB tables & test connection ──────────────────────────────────
    with app.app_context():
        try:
            from sqlalchemy import text
            # quick test
            db.session.execute(text("SELECT 1"))
            print("Database connection OK, creating tables if needed...")
            # Import your models so SQLAlchemy knows about them
            from app.models.models import (
                User, Supplier, Category, Product,
                InventoryTransaction, Notification,
                PurchaseOrder, PurchaseOrderItem, MLResult
            )
            db.create_all()
            print("All tables ensured.")
        except Exception as e:
            print("❌ Database setup error:", e)
            sys.exit(1)

    return app
