import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# OpenAI Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in .env file")

# API Ninjas Configuration
API_NINJAS_KEY = os.getenv('API_NINJAS_KEY')
if not API_NINJAS_KEY:
    raise ValueError("API_NINJAS_KEY not found in .env file")

# Flask Configuration
FLASK_ENV = os.getenv('FLASK_ENV', 'development')
FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'False') == 'True'

# File Upload Configuration
UPLOAD_FOLDER = 'data/uploads'
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB (larger for PDFs)
ALLOWED_EXTENSIONS = {'txt', 'pdf'}

# Inventory Configuration
INVENTORY_FILE = 'data/inventory.json'

# Meal Plans Configuration
MEAL_PLANS_FILE = 'data/meal_plans.json'

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('data', exist_ok=True)
