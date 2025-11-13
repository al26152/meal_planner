# Meal Planner - Developer Implementation Guide

## Overview

A local web application that processes voice transcriptions and PDF receipts to build a food inventory, then suggests recipes based on available ingredients. Designed to reduce food waste and encourage creative cooking.

**Key Features:**
- **Inventory Management:** Upload voice transcriptions (.txt) from Google Recorder or PDF receipts to build food inventory
- **Automatic Extraction:** OpenAI GPT-4o-mini intelligently extracts food items from transcriptions and receipts
- **Unified Recipe Finder:** "What Can I Cook?" feature finds recipes from saved recipes + API, sorted by how many ingredients you already have
- **Shopping List:** Quick add missing ingredients to a shopping list with checkbox tracking
- **User Recipe Curation:** Import recipes from URLs/YouTube, save favorites, tag them, and build your personal recipe library
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
│   ├── openai_client.py           # OpenAI API wrapper
│   ├── transcription_processor.py # Processes .txt transcription files
│   ├── receipt_handler.py         # Processes .pdf receipt files
│   ├── inventory_manager.py       # JSON-based inventory CRUD
│   ├── recipe_generator.py        # Unified recipe finder + meal planning
│   ├── shopping_list_manager.py   # Shopping list CRUD operations
│   ├── user_recipe_manager.py     # User-curated recipes storage
│   └── recipe_importer.py         # Import recipes from URLs/text
│
├── frontend/
│   ├── index.html                 # Main HTML template
│   └── static/
│       ├── styles.css             # Styling
│       └── script.js              # Client-side logic
│
└── data/
    ├── inventory.json             # Persisted inventory items
    └── uploads/
        ├── transcriptions/        # Uploaded .txt files
        └── receipts/              # Uploaded .pdf files
```

---

## Setup & Installation

### Prerequisites
- Python 3.11+ installed
- OpenAI API key (https://platform.openai.com/api/keys)
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
Copy `.env.template` to `.env` and add your OpenAI API key:
```bash
OPENAI_API_KEY=sk-proj-your-key-here
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

## Development Phases

### Phase 1: MVP ✅ COMPLETE
- [x] Flask backend setup
- [x] Voice transcription processing
- [x] PDF receipt parsing
- [x] Inventory storage & retrieval
- [x] Web interface (HTML/CSS/JS)
- [x] WiFi accessibility

### Phase 2: Receipt Integration (Ready)
- [ ] Cross-reference receipts with inventory
- [ ] Track usage prompts ("Did you use this?")
- [ ] Receipt history timeline
- [ ] Price tracking

### Phase 3: Recipe Suggestions (Planned)
- [ ] Recipe suggestion endpoint
- [ ] Query OpenAI with inventory
- [ ] Display recipes in UI
- [ ] Filter by dietary preferences

### Phase 4: Polish & Optimization (Future)
- [ ] OCR for receipt scanning
- [ ] Recipe rating/feedback
- [ ] Shopping list generation
- [ ] Database migration
- [ ] Mobile app wrapper

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

1. **Database:** SQLite/PostgreSQL for better querying
2. **Authentication:** User login for multi-user support
3. **Shopping List:** Auto-generate from missing recipe ingredients
4. **OCR:** Direct photo upload for receipt scanning
5. **Export:** CSV/PDF export of inventory
6. **Notifications:** Expiration alerts
7. **Recipes:** Full recipe database with ratings
8. **Mobile App:** React Native or Flutter wrapper
9. **Offline Mode:** Service worker for offline access
10. **Analytics:** Track food waste patterns

---

## License

Personal project. Use and modify as needed.

---

## Support

For issues or questions, refer to the main `README.md` or check the code comments.
