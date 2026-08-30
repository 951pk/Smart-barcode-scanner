import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "database", "inventory.db")
EXPORTS_DIR = os.path.join(BASE_DIR, "exports")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

# Default admin credentials
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin123"

# Ensure directories exist
os.makedirs(EXPORTS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)