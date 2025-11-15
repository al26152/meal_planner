# Meal Planner - Local Recipe & Inventory Management
**Last Updated:** November 15, 2025

## Overview

A local web application that processes voice transcriptions and PDF receipts to build a food inventory, then suggests recipes based on available ingredients. Designed to reduce food waste and encourage creative cooking.

**Key Features:**
- **Inventory Management:** Upload voice transcriptions (.txt) from Google Recorder or PDF receipts, OR manually add ingredients with natural language parsing
- **Quick Add Ingredient:** Type ingredients naturally (e.g., "2 lbs chicken, 3 tomatoes") and AI parses them automatically into your inventory
- **Automatic Extraction:** OpenAI GPT-4o-mini intelligently extracts food items from transcriptions and receipts
- **Unified Recipe Finder:** "What Can I Cook?" feature finds recipes from saved recipes + API, sorted by how many ingredients you already have
- **Shopping List:** Quick add missing ingredients to a shopping list with checkbox tracking
- **User Recipe Curation:** Import recipes from URLs/YouTube, save favorites, tag them, and build your personal recipe library
- **Button Feedback:** Visual feedback on all button interactions (color change + scale effect) for clear user feedback
- **Local Storage:** All data stored locally in JSON (no cloud sync)
- **WiFi Accessible:** Access from any device on same network at `http://[computer-ip]:5000`
- **Mobile Responsive:** Works great on phones, tablets, and desktops

---

## Project Architecture

### Tech Stack
- **Backend:** Python 3.11+ with Flask 3.0.0
- **Frontend:** HTML5, CSS3, Vanilla JavaScript (no frameworks)
- **AI Processing:** OpenAI API (GPT-4o-mini)
- **PDF Parsing:** pdfplumber 0.10.4
- **Storage:** JSON files (local filesystem)
- **Network:** Flask development server on `0.0.0.0:5000`

### Directory Structure

```
meal-planner/
├── app.py                          # Main Flask application
├── config.py                       # Configuration & environment variables
├── requirements.txt                # Python dependencies
├── .env                           # Environment variables (API keys) - DO NOT COMMIT
├── .env.template                  # Template for .env setup
├── .gitignore                     # Git ignore rules
│
├── backend/
│   ├── __init__.py
│   ├── openai_client.py           # OpenAI API wrapper + recipe adaptation
│   ├── transcription_processor.py # Processes .txt transcription files
│   ├── receipt_handler.py         # Processes .pdf receipt files
│   ├── inventory_manager.py       # JSON-based inventory CRUD
│   ├── recipe_generator.py        # Unified recipe finder + meal planning
│   ├── shopping_list_manager.py   # Shopping list CRUD operations
│   ├── shopping_list_generator.py # Generate shopping lists from meal plans
│   ├── user_recipe_manager.py     # User-curated recipes storage & search
│   ├── recipe_importer.py         # Import recipes from URLs/YouTube/text
│   ├── recipe_curator.py          # Recipe curation helpers
│   └── meal_plan_manager.py       # Meal plan storage & retrieval
│
├── frontend/
│   ├── index.html                 # Main HTML template
│   └── static/
│       ├── styles.css             # Styling (with dark mode)
│       ├── script.js              # Core client-side logic
│       └── recipes.js             # Recipe library UI logic
│
└── data/
    ├── inventory.json             # Persisted inventory items
    ├── user_recipes.json          # User's curated recipes
    ├── shopping_list.json         # Shopping list items
    ├── meal_plans.json            # Saved meal plans
    └── uploads/
        ├── transcriptions/        # Uploaded .txt files
        └── receipts/              # Uploaded .pdf files
```

---

## Setup & Installation

### Prerequisites
- Python 3.11+ installed
- OpenAI API key (https://platform.openai.com/api/keys)
- API Ninjas key for recipe search (https://api-ninjas.com/register)
- pip (Python package manager)

### Step-by-Step Setup

#### 1. Clone Repository
```bash
git clone https://github.com/al26152/meal_planner
cd meal_planner
```

#### 2. Create Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate  # Windows
# OR
source venv/bin/activate  # Mac/Linux
```

#### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 4. Create `.env` File
Copy `.env.template` to `.env` and add your API keys:
```bash
OPENAI_API_KEY=sk-proj-your-key-here
API_NINJAS_KEY=your-api-ninjas-key-here
FLASK_ENV=development
FLASK_DEBUG=True
```

#### 5. Run the Application
```bash
python app.py
```

The server will start on:
- **Computer:** http://localhost:5000
- **Mobile (same WiFi):** http://[YOUR_COMPUTER_IP]:5000

---

## API Endpoints

### Upload & Processing
```
POST /api/upload-transcription
```
Upload a `.txt` transcription or `.pdf` receipt file.

**Request:**
- Content-Type: `multipart/form-data`
- File types: `.txt` (text) or `.pdf` (receipts)
- Max file size: 10MB

**Response (Success):**
```json
{
  "success": true,
  "message": "Added 12 items from receipt to inventory",
  "items": [
    {
      "id": "uuid-string",
      "name": "butter",
      "quantity": 250,
      "unit": "grams",
      "category": "dairy",
      "added_date": "2025-11-09T09:15:00",
      "source": "receipt",
      "notes": ""
    }
  ]
}
```

**Response (Error):**
```json
{
  "error": "Only .txt and .pdf files are allowed"
}
```

### Inventory Management

#### Get All Items
```
GET /api/inventory
```
Returns all items in the inventory.

**Response:**
```json
{
  "success": true,
  "count": 25,
  "items": [...]
}
```

#### Delete Item
```
DELETE /api/inventory/{item_id}
```
Remove a specific item from inventory.

#### Update Item
```
PUT /api/inventory/{item_id}
```
Update an item's details (quantity, notes, etc.).

**Request Body:**
```json
{
  "quantity": 500,
  "unit": "grams",
  "notes": "Expiring soon",
  "category": "dairy"
}
```

#### Clear All Inventory
```
DELETE /api/inventory
```
Remove all items from inventory.

#### Quick Add Ingredient (Manual)
```
POST /api/inventory/add
```
Manually add ingredients with natural language parsing. OpenAI automatically parses free-text input into structured items.

**Request:**
```json
{
  "text": "2 lbs chicken, 3 tomatoes, 1 gallon milk"
}
```

**Response (Success):**
```json
{
  "success": true,
  "message": "Added 3 item(s) to inventory",
  "items": [
    {
      "id": "uuid-string",
      "name": "chicken",
      "quantity": 2,
      "unit": "lbs",
      "category": "meat",
      "added_date": "2025-11-15T14:30:00",
      "source": "manual",
      "notes": ""
    },
    {
      "id": "uuid-string",
      "name": "tomatoes",
      "quantity": 3,
      "unit": "pieces",
      "category": "produce",
      "added_date": "2025-11-15T14:30:00",
      "source": "manual",
      "notes": ""
    },
    {
      "id": "uuid-string",
      "name": "milk",
      "quantity": 1,
      "unit": "gallon",
      "category": "dairy",
      "added_date": "2025-11-15T14:30:00",
      "source": "manual",
      "notes": ""
    }
  ]
}
```

**Features:**
- Accepts natural language input (e.g., "2 lbs chicken", "3 tomatoes")
- Automatically detects quantity, unit, and category
- Parses multiple items separated by commas
- Returns parsed items added to inventory
- Source is automatically set to "manual"

### Meal Plans

#### Generate Meal Plan
```
POST /api/meal-plans/generate
```
Generate AI-powered meal plan based on current inventory.

**Request:**
```json
{
  "num_meals": 5,
  "criteria": "quick and asian-inspired",
  "use_curated": true
}
```

#### Get All Meal Plans
```
GET /api/meal-plans
```
Retrieve all saved meal plans.

#### Get Specific Meal Plan
```
GET /api/meal-plans/{plan_id}
```

#### Delete Meal Plan
```
DELETE /api/meal-plans/{plan_id}
```

#### Regenerate Single Meal
```
POST /api/meal-plans/{plan_id}/regenerate-meal
```
Regenerate just one meal in a plan.

#### Generate Shopping List from Plan
```
POST /api/meal-plans/{plan_id}/shopping-list
```
Create a shopping list of missing ingredients for a meal plan.

### Recipe Finding (Unified)

#### Find Recipes by Inventory
```
GET /api/recipes/find-by-inventory?preferences=optional&limit=10
```
Find recipes matching current inventory. **Prioritizes saved recipes first, then API recipes.** Results sorted by fewest missing ingredients.

**Response:**
```json
{
  "success": true,
  "count": 5,
  "source": "mixed",
  "recipes": [
    {
      "name": "Chicken Stir Fry",
      "source": "saved",
      "match_percentage": 100,
      "has_ingredients": ["chicken", "onion", "garlic"],
      "missing_ingredients": [],
      "instructions": "..."
    }
  ]
}
```

### Shopping List Management

#### Get Shopping List
```
GET /api/shopping-list
```
Get all active (non-completed) shopping list items.

#### Add to Shopping List
```
POST /api/shopping-list
```
Add missing ingredients to shopping list.

**Request:**
```json
{
  "items": [
    {"name": "tomatoes", "quantity": 2, "unit": "pieces"},
    {"name": "basil", "quantity": 1, "unit": "bunch"}
  ]
}
```

#### Update Item
```
PUT /api/shopping-list/{item_id}
```
Update item (e.g., mark as completed).

#### Remove Item
```
DELETE /api/shopping-list/{item_id}
```

#### Clear All
```
DELETE /api/shopping-list
```

### User Recipes Management

#### Get User Recipes
```
GET /api/user-recipes
```
Get all user-curated recipes with optional filtering.

**Query Parameters:**
- `q` - Search by recipe name
- `tags` - Filter by tags (e.g., `?tags=asian&tags=quick`)
- `ingredients` - Filter by ingredients

#### Create Recipe
```
POST /api/user-recipes
```
Create a new recipe manually or from imported data.

**Request:**
```json
{
  "name": "Chicken Stir Fry",
  "ingredients": ["chicken", "onion", "garlic", "soy sauce"],
  "instructions": "Heat oil, add chicken, then vegetables...",
  "tags": ["asian", "quick"],
  "notes": "Great weeknight meal"
}
```

#### Get Recipe by ID
```
GET /api/user-recipes/{recipe_id}
```

#### Update Recipe
```
PUT /api/user-recipes/{recipe_id}
```

#### Delete Recipe
```
DELETE /api/user-recipes/{recipe_id}
```

#### Get Recipes by Tag
```
GET /api/user-recipes/search-by-tag/{tag}
```

#### Match Recipes to Ingredients
```
POST /api/user-recipes/match-ingredients
```
Find recipes that use specified ingredients.

**Request:**
```json
{
  "ingredients": ["chicken", "garlic", "onion"]
}
```

#### Adapt Recipe to Inventory
```
GET /api/user-recipes/{recipe_id}/adapt
```
Get AI adaptation analysis showing which ingredients you have and what's missing.

### Recipe Import

#### Import Recipe from URL or Text
```
POST /api/recipes/import
```
Import recipes from website URLs, YouTube videos, or plain text.

**Request (URL):**
```json
{
  "url": "https://www.example.com/recipe/chicken-stir-fry",
  "tags": ["asian", "quick"],
  "notes": "Found on food blog"
}
```

**Request (YouTube):**
```json
{
  "url": "https://youtube.com/watch?v=...",
  "tags": ["video-recipe"]
}
```

**Request (Text Content):**
```json
{
  "content": "Chicken Stir Fry\nIngredients: chicken, soy sauce...\nInstructions: ...",
  "tags": ["quick"]
}
```

---

## Core Modules

### 1. OpenAI Client (`backend/openai_client.py`)

**Functions:**

- `extract_receipt_items(receipt_text: str) -> list`
  - Parses text from PDF receipts
  - Returns structured items: name, quantity, unit, category

- `extract_inventory_items(transcription_text: str) -> list`
  - Parses voice transcription text
  - Returns structured items with same format

**Prompt Strategy:**
- Uses GPT-4o-mini (cost-effective, good accuracy)
- Temperature: 0.3 (deterministic extraction)
- Extracts: name, quantity, unit, category

### 2. Transcription Processor (`backend/transcription_processor.py`)

- `process_transcription_file(file_path: str) -> list`
  - Reads uploaded .txt file
  - Sends to OpenAI for extraction
  - Returns list of items

- `save_uploaded_file(file, filename: str) -> str`
  - Saves file to `data/uploads/transcriptions/`
  - Returns file path

### 3. Receipt Handler (`backend/receipt_handler.py`)

- `process_receipt_file(file_path: str) -> list`
  - Extracts text from PDF using pdfplumber
  - Sends to OpenAI for parsing
  - Returns list of items

- `extract_text_from_pdf(file_path: str) -> str`
  - Uses pdfplumber to read all pages
  - Concatenates text from all pages
  - Handles encoding errors gracefully

- `save_uploaded_file(file, filename: str) -> str`
  - Saves file to `data/uploads/receipts/`
  - Returns file path

### 4. Inventory Manager (`backend/inventory_manager.py`)

JSON-based inventory storage with CRUD operations.

**Key Methods:**

```python
# Load inventory from JSON
inventory = InventoryManager.load_inventory()

# Add single item
item = InventoryManager.add_item(
    name="butter",
    quantity=250,
    unit="grams",
    category="dairy",
    source="receipt"
)

# Add multiple items at once
items = InventoryManager.add_items_batch(items_list, source="receipt")

# Get all items
all_items = InventoryManager.get_all_items()

# Get single item by ID
item = InventoryManager.get_item_by_id(item_id)

# Update item
updated = InventoryManager.update_item(item_id, quantity=500, notes="...")

# Delete item
success = InventoryManager.delete_item(item_id)

# Clear all items
InventoryManager.clear_inventory()
```

### 5. Flask App (`app.py`)

Main application with route definitions.

**Features:**
- Static file serving from `frontend/static/`
- Template rendering from `frontend/`
- Error handlers for common issues
- File upload validation

---

## Data Models

### Inventory Item
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "butter",
  "quantity": 250,
  "unit": "grams",
  "category": "dairy",
  "added_date": "2025-11-09T09:15:32.456789",
  "source": "receipt",
  "notes": ""
}
```

**Fields:**
- `id`: UUID (auto-generated)
- `name`: lowercase item name
- `quantity`: numeric amount
- `unit`: measurement unit (grams, ml, pieces, pack, etc.)
- `category`: food category (dairy, produce, meat, pantry, frozen, beverages, bakery, other)
- `added_date`: ISO 8601 timestamp
- `source`: `receipt` or `transcription`
- `notes`: user notes (optional)

### Inventory JSON Structure
```json
[
  { item object },
  { item object },
  ...
]
```

---

## Configuration

### Environment Variables (`.env`)

```
OPENAI_API_KEY=sk-proj-your-api-key
FLASK_ENV=development
FLASK_DEBUG=True
```

### Config File (`config.py`)

Key settings:
- `UPLOAD_FOLDER`: `data/uploads`
- `MAX_FILE_SIZE`: 10MB
- `ALLOWED_EXTENSIONS`: {txt, pdf}
- `INVENTORY_FILE`: `data/inventory.json`

---

## Development Workflow

### Running Locally
```bash
# Activate venv
venv\Scripts\activate

# Start Flask (auto-reload on file changes)
python app.py

# Visit http://localhost:5000
```

### Adding New Features

1. **Backend Logic:**
   - Add function to relevant module (e.g., `inventory_manager.py`)
   - Add Flask route in `app.py`

2. **Frontend:**
   - Update HTML in `frontend/index.html`
   - Add styles to `frontend/static/styles.css`
   - Add JavaScript to `frontend/static/script.js`

3. **Testing:**
   - Test locally at http://localhost:5000
   - Test from mobile on same WiFi

### Security Notes
- `.env` file MUST be in `.gitignore` (contains API keys)
- Never commit API keys to GitHub
- Flask development server is NOT for production
- Add authentication if accessed outside home network

---

## Deployment (Future)

When moving to production:

1. **Replace Flask with Production Server:**
   - Use Gunicorn or uWSGI
   - Add nginx reverse proxy
   - Enable HTTPS

2. **Data Backup:**
   - Set up regular backups of `data/inventory.json`
   - Consider SQLite for larger datasets

3. **Environment:**
   - Use environment variables for all config
   - Separate dev/prod configs

4. **Scaling:**
   - Move to database (PostgreSQL, SQLite)
   - Implement user authentication
   - Add recipe suggestion caching

---

## Recent Changes & Fixes

### November 15, 2025 - Quick Add Ingredient & Button Feedback
**New Features:**
- **Quick Add Ingredient:** Manually add ingredients with natural language parsing
  - New endpoint: `POST /api/inventory/add`
  - Accepts free-text input (e.g., "2 lbs chicken, 3 tomatoes, 1 gallon milk")
  - OpenAI GPT-4o-mini automatically parses quantity, unit, and category
  - Handles multiple items separated by commas
  - Items added with "manual" source for tracking

- **Button Click Feedback:** Visual feedback on all button interactions
  - Added `:active` pseudo-classes to all button types
  - Color change on click (darker shade) + 98% scale effect
  - Smooth transitions for professional feel
  - Applied to: primary, secondary, danger, and small buttons
  - Provides immediate user feedback that button was pressed

**Frontend Enhancements:**
- New "Quick Add Ingredient" form in Inventory tab
- Text input with helpful placeholder examples
- Loading state shows "Adding..." during processing
- Enter key support for quick submission
- Error handling with user-friendly messages
- Success messages with item count

**Documentation Updates:**
- Updated README with new features and API endpoints
- Added quick add endpoint documentation
- Updated .gitignore to prevent accidental "nul" file creation
- Comprehensive feature list reflects current capabilities

### November 13, 2025 - Unified Recipe Finder Refactor
**What Changed:**
- Consolidated recipe finding into single unified endpoint (`/api/recipes/find-by-inventory`)
- Eliminated duplicate recipe search logic (removed old 2-step process)
- Integrated shopping list management with recipe finding
- Simplified frontend UI with "What Can I Cook?" tab

**Key Improvements:**
- User's saved recipes now prioritized over API results
- Single-click add missing ingredients to shopping list
- Reduced code complexity and improved maintainability
- Better mobile experience

### November 11, 2025 - System Stability & Recipe Curation
**Critical Crash Fix:**
- Fixed memory exhaustion crash caused by combinatorial explosion
- Problem: 30 ingredients = 155 million combinations = 5-10GB RAM needed
- Solution: Implemented smart random sampling algorithm
- Added 60-second timeouts to all OpenAI API calls (prevents hanging)

**New Features:**
- User recipe manager: Save, import, and curate recipes
- Recipe importer: Extract recipes from URLs, YouTube, and plain text
- Recipe adaptation: AI analyzes recipe vs your inventory, suggests substitutions
- Recipe prioritization: Your curated recipes take priority over API results
- Enhanced meal planning with curated recipe integration

---

## Development Phases

### Phase 1: MVP ✅ COMPLETE
- [x] Flask backend setup
- [x] Voice transcription processing (Google Recorder .txt files)
- [x] PDF receipt parsing with text extraction
- [x] Inventory storage & retrieval (JSON-based)
- [x] Web interface (HTML5/CSS3/Vanilla JS)
- [x] WiFi accessibility (0.0.0.0:5000)

### Phase 2: Recipe Integration ✅ COMPLETE
- [x] Unified recipe finder endpoint
- [x] Query OpenAI + API Ninjas for recipes
- [x] Match recipes to current inventory
- [x] Sort by ingredient availability
- [x] Display recipes with match percentage
- [x] Show missing ingredients

### Phase 3: User Recipe Curation ✅ COMPLETE (Nov 11)
- [x] User recipe storage (JSON-based)
- [x] Recipe CRUD operations (Create, Read, Update, Delete)
- [x] Import recipes from URLs/YouTube
- [x] AI-powered recipe import (auto-extracts ingredients, instructions)
- [x] Tag and search recipes
- [x] Recipe adaptation analysis (what you have vs missing)
- [x] Prioritize user recipes over API results

### Phase 4: Shopping List Management ✅ COMPLETE (Nov 13)
- [x] Shopping list CRUD operations
- [x] Quick add missing ingredients from recipes
- [x] Mark items as completed
- [x] Generate shopping list from meal plans
- [x] Persistent storage
- [x] Category organization

### Phase 5: System Optimization ✅ COMPLETE (Nov 11)
- [x] Fixed memory crash (replaced combinatorial explosion with smart sampling)
- [x] Added 60s timeouts to OpenAI API calls
- [x] Prevent hanging requests
- [x] Recipe prioritization logic

### Phase 6: Inventory & UX Enhancements ✅ COMPLETE (Nov 15)
- [x] Quick add ingredient with natural language parsing
- [x] OpenAI integration for ingredient parsing
- [x] Button click visual feedback (color change + scale)
- [x] Loading state indicators on button interactions
- [x] Enter key support for form submission
- [x] Error handling and user-friendly messages

### Phase 7: Polish & Enhancement (In Progress)
- [ ] OCR for receipt scanning
- [ ] Recipe rating/feedback system
- [ ] Cooking history tracking
- [ ] Nutritional information
- [ ] Batch meal planning
- [ ] Expiration date tracking & alerts
- [ ] Recipe export (PDF/CSV)
- [ ] Multi-user support with authentication
- [ ] Database migration (SQLite/PostgreSQL)
- [ ] Mobile app wrapper
- [ ] Offline mode with Service Workers
- [ ] Food waste analytics

---

## Troubleshooting

### "OPENAI_API_KEY not found in .env file"
- Ensure `.env` file exists in project root
- Add your OpenAI API key to the file
- Restart Flask app

### "No food items found in receipt"
- Check PDF is readable and contains text
- Verify items are visible in PDF
- Try a different receipt format

### "File is too large"
- Max file size is 10MB
- Compress or split large files

### CSS/JS not loading
- Clear browser cache (Ctrl+Shift+Delete)
- Check `frontend/static/` folder exists
- Verify Flask reloaded after changes

### Mobile can't access app
- Ensure both devices on same WiFi network
- Use correct computer IP (e.g., http://192.168.1.233:5000)
- Check firewall allows port 5000

---

## Dependencies & Versions

```
flask==3.0.0                    # Web framework
python-dotenv==1.0.0           # Environment variables
openai>=2.7.0                  # OpenAI API client
requests==2.31.0               # HTTP library
pdfplumber==0.10.4             # PDF text extraction
```

---

## Performance Notes

### API Costs
- GPT-4o-mini: ~$0.15 per 1M input tokens
- Estimate: $0.002-0.005 per receipt/transcription
- Budget: $0.10-0.20 per week

### Processing Time
- Text transcription: 2-3 seconds
- PDF receipt: 3-5 seconds (includes PDF parsing)

### Storage
- Each item: ~200 bytes JSON
- 1000 items: ~200KB
- No storage limits for local deployment

---

## Future Enhancements

### Already Implemented ✅
- Shopping list management with CRUD operations
- User recipe library with import/export from URLs
- Recipe matching to inventory
- AI-powered recipe adaptation

### Planned Enhancements 🚀
1. **OCR Integration:** Direct photo upload for receipt scanning (smartphone camera)
2. **Recipe Ratings:** User ratings and reviews of recipes
3. **Cooking History:** Track which recipes you've cooked and results
4. **Nutritional Analysis:** Calorie, macro, and micronutrient tracking
5. **Meal Planning:** Generate 7-day meal plans based on preferences
6. **Expiration Tracking:** Alerts for ingredients expiring soon
7. **Export Features:** CSV/PDF export of inventory and shopping lists
8. **Database Migration:** Move from JSON to SQLite/PostgreSQL for scalability
9. **Authentication:** User accounts for multi-user scenarios
10. **Mobile App:** Native iOS/Android wrapper with offline mode
11. **Analytics Dashboard:** Track food waste patterns and savings
12. **Recipe Suggestions:** Learn from your cooking preferences

---

## License

Personal project. Use and modify as needed.

---

## Support

For issues or questions, refer to the main `README.md` or check the code comments.
