import os
import sys
import traceback

# Try to import dotenv, install if necessary
try:
    from dotenv import load_dotenv
    print("Starting AI Inventory Tracker...")
except ImportError:
    print("dotenv module not found. Installing python-dotenv...")
    import subprocess
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "python-dotenv==1.0.0"])
        print("✅ python-dotenv installed successfully")
        from dotenv import load_dotenv
    except Exception as e:
        print(f"❌ Failed to install python-dotenv: {e}")
        print("Please install it manually with: pip install python-dotenv==1.0.0")
        sys.exit(1)

# Load environment variables
print("Loading environment variables...")
load_dotenv()

try:
    print("Importing Flask application...")
    from app import create_app
    from waitress import serve
    
    print("Creating Flask application instance...")
    app = create_app()
    
    if __name__ == "__main__":
        # For development
        if os.environ.get('FLASK_ENV') == 'development':
            print("Starting development server...")
            app.run(debug=True)
        else:
            # For production
            print("Starting production server...")
            port = int(os.environ.get("PORT", 5000))
            serve(app, host="0.0.0.0", port=port)
            
except ImportError as e:
    print(f"ERROR: Failed to import required modules: {str(e)}")
    print("Please ensure you've installed all requirements with: pip install -r requirements.txt")
    print("Make sure you've activated your virtual environment with: venv\\Scripts\\activate")
    sys.exit(1)
    
except Exception as e:
    print(f"ERROR: An unexpected error occurred during startup: {str(e)}")
    print("Stack trace:")
    traceback.print_exc()
    sys.exit(1)
