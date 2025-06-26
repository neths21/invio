import os
import sys
import traceback

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Environment variables loaded")
except ImportError:
    print("⚠️ python-dotenv not found — skipping .env loading")

# Create and expose the Flask app
try:
    print("📦 Importing Flask app...")
    from app import create_app

    print("🚀 Creating app instance...")
    app = create_app()  # ✅ Vercel looks for this

except ImportError as e:
    print(f"❌ ImportError: {e}")
    print("➡️ Run: pip install -r requirements.txt")
    sys.exit(1)

except Exception as e:
    print(f"❌ Unexpected error: {e}")
    traceback.print_exc()
    sys.exit(1)
