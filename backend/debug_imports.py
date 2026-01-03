import os
import sys

print("=== DEBUGGING IMPORTS ===")
print(f"Current directory: {os.getcwd()}")
print(f"Python path: {sys.path}")

# Check if app directory exists
app_path = os.path.join(os.getcwd(), 'app')
print(f"App directory exists: {os.path.exists(app_path)}")

# Check if models directory exists
models_path = os.path.join(app_path, 'models')
print(f"Models directory exists: {os.path.exists(models_path)}")

# List files in models directory
if os.path.exists(models_path):
    print("Files in models directory:")
    for file in os.listdir(models_path):
        print(f"  - {file}")

# Try to import step by step
print("\n=== STEP BY STEP IMPORTS ===")
try:
    print("1. Importing app...")
    import app
    print("   ✅ app imported")
except Exception as e:
    print(f"   ❌ app import failed: {e}")

try:
    print("2. Importing app.models...")
    import app.models
    print("   ✅ app.models imported")
    
    # Check what's in app.models
    print(f"   Contents of app.models: {dir(app.models)}")
except Exception as e:
    print(f"   ❌ app.models import failed: {e}")

try:
    print("3. Importing specific model...")
    from app.models.document_model import LegalDocument
    print("   ✅ LegalDocument imported directly")
except Exception as e:
    print(f"   ❌ LegalDocument direct import failed: {e}")

try:
    print("4. Importing from models package...")
    from app.models import LegalDocument
    print("   ✅ LegalDocument imported from package")
except Exception as e:
    print(f"   ❌ LegalDocument package import failed: {e}")