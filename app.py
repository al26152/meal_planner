from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import os
from config import FLASK_DEBUG, FLASK_ENV, UPLOAD_FOLDER, MAX_FILE_SIZE, ALLOWED_EXTENSIONS
from backend.transcription_processor import process_transcription_file
from backend.receipt_handler import process_receipt_file, save_uploaded_file as save_receipt_file
from backend.inventory_manager import InventoryManager
from backend.meal_plan_manager import MealPlanManager
from backend.recipe_generator import generate_meal_plan, generate_unified_meal_plan, regenerate_single_meal, generate_meal_plan_with_curated
from backend.openai_client import adapt_recipe_to_inventory, parse_manual_ingredient
from backend.shopping_list_generator import generate_shopping_list
from backend.user_recipe_manager import UserRecipeManager
from backend.recipe_importer import import_recipe_from_url, import_recipe_from_youtube, extract_recipe_from_text
from backend.planning_manager import PlanningManager

app = Flask(__name__, template_folder='frontend', static_folder='frontend/static', static_url_path='/static')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ===== Frontend Routes =====

@app.route('/')
def index():
    """Serve the main page."""
    return render_template('index.html')


# ===== API Routes =====

@app.route('/api/upload-transcription', methods=['POST'])
def upload_transcription():
    """Upload and process a transcription or receipt file."""

    # Check if file is in request
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Only .txt and .pdf files are allowed'}), 400

    try:
        filename = secure_filename(file.filename)
        file_ext = filename.rsplit('.', 1)[1].lower()

        # Route based on file type
        if file_ext == 'txt':
            # Handle text transcription
            from backend.transcription_processor import save_uploaded_file
            file_path = save_uploaded_file(file, filename)
            source = 'transcription'
            extracted_items = process_transcription_file(file_path)

        elif file_ext == 'pdf':
            # Handle PDF receipt
            file_path = save_receipt_file(file, filename)
            source = 'receipt'
            extracted_items = process_receipt_file(file_path)

        else:
            return jsonify({'error': 'Unsupported file type'}), 400

        if not file_path:
            return jsonify({'error': 'Failed to save file'}), 500

        if not extracted_items:
            return jsonify({'error': f'No food items found in {source}'}), 400

        # Add items to inventory
        added_items = InventoryManager.add_items_batch(extracted_items, source=source)

        return jsonify({
            'success': True,
            'message': f'Added {len(added_items)} items from {source} to inventory',
            'items': added_items
        }), 200

    except Exception as e:
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500


@app.route('/api/inventory', methods=['GET'])
def get_inventory():
    """Get all inventory items."""
    try:
        items = InventoryManager.get_all_items()
        return jsonify({
            'success': True,
            'count': len(items),
            'items': items
        }), 200
    except Exception as e:
        return jsonify({'error': f'Error retrieving inventory: {str(e)}'}), 500


@app.route('/api/inventory/<item_id>', methods=['DELETE'])
def delete_item(item_id):
    """Delete an item from inventory."""
    try:
        success = InventoryManager.delete_item(item_id)

        if success:
            return jsonify({'success': True, 'message': 'Item deleted'}), 200
        else:
            return jsonify({'error': 'Item not found'}), 404

    except Exception as e:
        return jsonify({'error': f'Error deleting item: {str(e)}'}), 500


@app.route('/api/inventory/<item_id>', methods=['PUT'])
def update_item(item_id):
    """Update an item in inventory."""
    try:
        data = request.json

        updated_item = InventoryManager.update_item(
            item_id,
            name=data.get('name'),
            quantity=data.get('quantity'),
            unit=data.get('unit'),
            notes=data.get('notes'),
            category=data.get('category')
        )

        if updated_item:
            return jsonify({'success': True, 'item': updated_item}), 200
        else:
            return jsonify({'error': 'Item not found'}), 404

    except Exception as e:
        return jsonify({'error': f'Error updating item: {str(e)}'}), 500


@app.route('/api/inventory', methods=['DELETE'])
def clear_inventory():
    """Clear all items from inventory."""
    try:
        InventoryManager.clear_inventory()
        return jsonify({'success': True, 'message': 'Inventory cleared'}), 200
    except Exception as e:
        return jsonify({'error': f'Error clearing inventory: {str(e)}'}), 500


@app.route('/api/inventory/add', methods=['POST'])
def add_inventory_item():
    """Add a single item to inventory manually via free-text input."""
    try:
        data = request.json
        user_input = data.get('text', '').strip()

        if not user_input:
            return jsonify({'error': 'Please enter an ingredient'}), 400

        # Parse the user input using OpenAI
        parsed_items = parse_manual_ingredient(user_input)

        if not parsed_items:
            return jsonify({'error': 'Could not parse the ingredient. Please try again with a clearer description (e.g., "2 lbs chicken" or "3 tomatoes")'}), 400

        # Add items to inventory
        added_items = InventoryManager.add_items_batch(parsed_items, source='manual')

        return jsonify({
            'success': True,
            'message': f'Added {len(added_items)} item(s) to inventory',
            'items': added_items
        }), 200

    except Exception as e:
        return jsonify({'error': f'Error adding item: {str(e)}'}), 500


# ===== Meal Planning Routes =====

@app.route('/api/meal-plans/generate', methods=['POST'])
def generate_meal_plan_endpoint():
    """Generate a new meal plan."""
    try:
        data = request.json
        num_meals = data.get('num_meals')
        criteria = data.get('criteria', '')
        use_curated = data.get('use_curated', True)  # Default to using curated recipes

        if not num_meals:
            return jsonify({'error': 'num_meals is required'}), 400

        # Get current inventory
        inventory = InventoryManager.get_all_items()

        # Generate meal plan - prioritize curated recipes if available
        if use_curated:
            result = generate_meal_plan_with_curated(num_meals, criteria, inventory)
        else:
            result = generate_unified_meal_plan(num_meals, criteria, inventory)

        if not result.get('success'):
            return jsonify({'error': result.get('error', 'Failed to generate meal plan')}), 400

        # Save the meal plan
        meals = result.get('meals', [])
        from datetime import datetime
        now = datetime.now().isoformat()
        meal_plan = MealPlanManager.create_meal_plan(now, now, criteria, meals)

        return jsonify({
            'success': True,
            'message': result.get('message', f'Generated {result.get("count")} delicious meals'),
            'plan_id': meal_plan['id'],
            'meals': meals
        }), 200

    except Exception as e:
        return jsonify({'error': f'Error generating meal plan: {str(e)}'}), 500


@app.route('/api/meal-plans', methods=['GET'])
def get_meal_plans():
    """Get all saved meal plans."""
    try:
        plans = MealPlanManager.get_all_meal_plans()
        return jsonify({
            'success': True,
            'count': len(plans),
            'plans': plans
        }), 200
    except Exception as e:
        return jsonify({'error': f'Error retrieving meal plans: {str(e)}'}), 500


@app.route('/api/meal-plans/<plan_id>', methods=['GET'])
def get_meal_plan(plan_id):
    """Get a specific meal plan."""
    try:
        plan = MealPlanManager.get_meal_plan_by_id(plan_id)

        if not plan:
            return jsonify({'error': 'Meal plan not found'}), 404

        return jsonify({
            'success': True,
            'plan': plan
        }), 200

    except Exception as e:
        return jsonify({'error': f'Error retrieving meal plan: {str(e)}'}), 500


@app.route('/api/meal-plans/<plan_id>', methods=['DELETE'])
def delete_meal_plan(plan_id):
    """Delete a meal plan."""
    try:
        success = MealPlanManager.delete_meal_plan(plan_id)

        if success:
            return jsonify({'success': True, 'message': 'Meal plan deleted'}), 200
        else:
            return jsonify({'error': 'Meal plan not found'}), 404

    except Exception as e:
        return jsonify({'error': f'Error deleting meal plan: {str(e)}'}), 500


@app.route('/api/meal-plans/<plan_id>/regenerate-meal', methods=['POST'])
def regenerate_meal(plan_id):
    """Regenerate a single meal in a plan."""
    try:
        data = request.json
        meal_index = data.get('meal_index')
        criteria = data.get('criteria', '')

        if meal_index is None:
            return jsonify({'error': 'meal_index is required'}), 400

        # Get meal plan
        plan = MealPlanManager.get_meal_plan_by_id(plan_id)
        if not plan:
            return jsonify({'error': 'Meal plan not found'}), 404

        if meal_index < 0 or meal_index >= len(plan.get('meals', [])):
            return jsonify({'error': 'Invalid meal index'}), 400

        # Get current inventory
        inventory = InventoryManager.get_all_items()

        # Regenerate the meal
        result = regenerate_single_meal(meal_index, criteria, inventory)

        if not result.get('success'):
            return jsonify({'error': result.get('error', 'Failed to regenerate meal')}), 400

        # Update the meal in the plan using meal index as identifier
        recipe = result.get('recipe')
        # Create a temp date key for the update (using meal index)
        temp_date_key = f"meal_{meal_index}"
        updated_plan = MealPlanManager.update_single_meal(plan_id, temp_date_key, recipe)

        if not updated_plan:
            return jsonify({'error': 'Failed to update meal plan'}), 500

        return jsonify({
            'success': True,
            'message': 'Meal regenerated successfully',
            'recipe': recipe
        }), 200

    except Exception as e:
        return jsonify({'error': f'Error regenerating meal: {str(e)}'}), 500


@app.route('/api/meal-plans/<plan_id>/shopping-list', methods=['POST'])
def get_shopping_list(plan_id):
    """Generate a shopping list for a meal plan."""
    try:
        plan = MealPlanManager.get_meal_plan_by_id(plan_id)

        if not plan:
            return jsonify({'error': 'Meal plan not found'}), 404

        # Get current inventory
        inventory = InventoryManager.get_all_items()

        # Generate shopping list
        shopping_list = generate_shopping_list(plan, inventory)

        return jsonify({
            'success': True,
            'shopping_list': shopping_list.get('by_category', {}),
            'total_missing_items': shopping_list.get('total_missing_items', 0),
            'items': shopping_list.get('shopping_list', [])
        }), 200

    except Exception as e:
        return jsonify({'error': f'Error generating shopping list: {str(e)}'}), 500


# ===== Shopping List Management =====

@app.route('/api/shopping-list', methods=['GET'])
def get_shopping_list_items():
    """Get current shopping list."""
    try:
        from backend.shopping_list_manager import ShoppingListManager

        items = ShoppingListManager.load_shopping_list()
        active_items = [item for item in items if not item.get('completed', False)]

        return jsonify({
            'success': True,
            'count': len(active_items),
            'items': active_items
        }), 200

    except Exception as e:
        return jsonify({'error': f'Error retrieving shopping list: {str(e)}'}), 500


@app.route('/api/shopping-list', methods=['POST'])
def add_to_shopping_list():
    """Add items to shopping list."""
    try:
        from backend.shopping_list_manager import ShoppingListManager

        data = request.json
        items_to_add = data.get('items', [])

        if not items_to_add:
            return jsonify({'error': 'No items provided'}), 400

        # Add items (handles duplicates by summing quantities)
        updated_list = ShoppingListManager.add_items_batch(items_to_add)

        return jsonify({
            'success': True,
            'message': f'Added {len(items_to_add)} items to shopping list',
            'items': updated_list
        }), 200

    except Exception as e:
        return jsonify({'error': f'Error adding items: {str(e)}'}), 500


@app.route('/api/shopping-list/<item_id>', methods=['PUT'])
def update_shopping_list_item(item_id):
    """Update shopping list item (e.g., mark as completed)."""
    try:
        from backend.shopping_list_manager import ShoppingListManager

        data = request.json
        updated_item = ShoppingListManager.update_item(item_id, **data)

        if not updated_item:
            return jsonify({'error': 'Item not found'}), 404

        return jsonify({
            'success': True,
            'item': updated_item
        }), 200

    except Exception as e:
        return jsonify({'error': f'Error updating item: {str(e)}'}), 500


@app.route('/api/shopping-list/<item_id>', methods=['DELETE'])
def remove_from_shopping_list(item_id):
    """Remove item from shopping list."""
    try:
        from backend.shopping_list_manager import ShoppingListManager

        ShoppingListManager.delete_item(item_id)

        return jsonify({
            'success': True,
            'message': 'Item removed from shopping list'
        }), 200

    except Exception as e:
        return jsonify({'error': f'Error removing item: {str(e)}'}), 500


@app.route('/api/shopping-list', methods=['DELETE'])
def clear_shopping_list():
    """Clear all items from shopping list."""
    try:
        from backend.shopping_list_manager import ShoppingListManager

        ShoppingListManager.clear_shopping_list()

        return jsonify({
            'success': True,
            'message': 'Shopping list cleared'
        }), 200

    except Exception as e:
        return jsonify({'error': f'Error clearing shopping list: {str(e)}'}), 500


# ===== User Recipe Management =====

recipe_manager = UserRecipeManager('data')


@app.route('/api/user-recipes', methods=['GET'])
def get_user_recipes():
    """Get all user-curated recipes with optional filtering."""
    try:
        # Get optional query parameters
        query = request.args.get('q', None)  # Search by name
        tags = request.args.getlist('tags')  # Filter by tags
        ingredients = request.args.getlist('ingredients')  # Filter by ingredients

        # Search recipes
        if query or tags or ingredients:
            recipes = recipe_manager.search_recipes(
                query=query,
                tags=tags if tags else None,
                ingredients=ingredients if ingredients else None
            )
        else:
            recipes = recipe_manager.get_all_recipes()

        return jsonify({
            'success': True,
            'count': len(recipes),
            'recipes': recipes
        }), 200

    except Exception as e:
        return jsonify({'error': f'Error fetching recipes: {str(e)}'}), 500


@app.route('/api/user-recipes/<recipe_id>', methods=['GET'])
def get_user_recipe(recipe_id):
    """Get a specific user recipe by ID."""
    try:
        recipe = recipe_manager.get_recipe(recipe_id)

        if not recipe:
            return jsonify({'error': 'Recipe not found'}), 404

        return jsonify({
            'success': True,
            'recipe': recipe
        }), 200

    except Exception as e:
        return jsonify({'error': f'Error fetching recipe: {str(e)}'}), 500


@app.route('/api/user-recipes', methods=['POST'])
def create_user_recipe():
    """Create a new user recipe."""
    try:
        data = request.get_json()

        # Validate required fields
        required = ['name', 'ingredients', 'instructions']
        if not all(field in data for field in required):
            return jsonify({'error': f'Missing required fields: {", ".join(required)}'}), 400

        # Create recipe
        recipe = recipe_manager.add_recipe(
            name=data['name'],
            ingredients=data['ingredients'],
            instructions=data['instructions'],
            source=data.get('source', 'manual'),
            source_url=data.get('source_url'),
            tags=data.get('tags', []),
            notes=data.get('notes', '')
        )

        return jsonify({
            'success': True,
            'message': 'Recipe created successfully',
            'recipe': recipe
        }), 201

    except Exception as e:
        return jsonify({'error': f'Error creating recipe: {str(e)}'}), 500


@app.route('/api/user-recipes/<recipe_id>', methods=['PUT'])
def update_user_recipe(recipe_id):
    """Update a user recipe."""
    try:
        data = request.get_json()

        # Update recipe (allows any valid fields)
        recipe = recipe_manager.update_recipe(recipe_id, **data)

        if not recipe:
            return jsonify({'error': 'Recipe not found'}), 404

        return jsonify({
            'success': True,
            'message': 'Recipe updated successfully',
            'recipe': recipe
        }), 200

    except Exception as e:
        return jsonify({'error': f'Error updating recipe: {str(e)}'}), 500


@app.route('/api/user-recipes/<recipe_id>', methods=['DELETE'])
def delete_user_recipe(recipe_id):
    """Delete a user recipe."""
    try:
        deleted = recipe_manager.delete_recipe(recipe_id)

        if not deleted:
            return jsonify({'error': 'Recipe not found'}), 404

        return jsonify({
            'success': True,
            'message': 'Recipe deleted successfully'
        }), 200

    except Exception as e:
        return jsonify({'error': f'Error deleting recipe: {str(e)}'}), 500


@app.route('/api/user-recipes/search-by-tag/<tag>', methods=['GET'])
def get_recipes_by_tag(tag):
    """Get all recipes with a specific tag."""
    try:
        recipes = recipe_manager.get_recipes_by_tag(tag)

        return jsonify({
            'success': True,
            'tag': tag,
            'count': len(recipes),
            'recipes': recipes
        }), 200

    except Exception as e:
        return jsonify({'error': f'Error searching recipes: {str(e)}'}), 500


@app.route('/api/user-recipes/match-ingredients', methods=['POST'])
def get_recipes_matching_ingredients():
    """Get recipes that use specified ingredients from your inventory."""
    try:
        data = request.get_json()
        ingredients = data.get('ingredients', [])

        if not ingredients:
            return jsonify({'error': 'No ingredients provided'}), 400

        recipes = recipe_manager.get_recipes_with_ingredients(ingredients)

        return jsonify({
            'success': True,
            'ingredients_searched': ingredients,
            'count': len(recipes),
            'recipes': recipes
        }), 200

    except Exception as e:
        return jsonify({'error': f'Error matching ingredients: {str(e)}'}), 500


@app.route('/api/user-recipes/<recipe_id>/adapt', methods=['GET'])
def adapt_recipe(recipe_id):
    """Adapt a user recipe to available inventory."""
    try:
        # Get the recipe
        recipe = recipe_manager.get_recipe(recipe_id)
        if not recipe:
            return jsonify({'error': 'Recipe not found'}), 404

        # Get current inventory
        inventory = InventoryManager.get_all_items()

        if not inventory:
            return jsonify({
                'success': True,
                'message': 'No inventory items available',
                'recipe': recipe,
                'adaptation': {
                    'can_make': False,
                    'match_percentage': 0,
                    'notes': 'Add items to your inventory to get adaptation suggestions'
                }
            }), 200

        # Adapt the recipe
        adapted = adapt_recipe_to_inventory(recipe, inventory)

        return jsonify({
            'success': True,
            'recipe': adapted
        }), 200

    except Exception as e:
        return jsonify({'error': f'Error adapting recipe: {str(e)}'}), 500


@app.route('/api/recipes/import', methods=['POST'])
def import_recipe_endpoint():
    """Import a recipe from a URL or text content."""
    try:
        data = request.get_json()

        # Option 1: Import from URL
        if 'url' in data:
            url = data['url']

            # Detect source type
            if 'youtube.com' in url or 'youtu.be' in url:
                recipe = import_recipe_from_youtube(url)
            else:
                recipe = import_recipe_from_url(url)

            if not recipe:
                return jsonify({'error': 'Failed to extract recipe from URL. Please verify the URL is a valid recipe page.'}), 400

            # Check if extraction requires manual completion (visual-only videos, etc.)
            if recipe.get('needs_manual_entry'):
                return jsonify({
                    'success': True,
                    'needs_manual_entry': True,
                    'message': recipe.get('reason', 'Please complete the recipe details'),
                    'recipe': recipe  # Return partial recipe for frontend to populate
                }), 200

            # Save to user recipes
            saved_recipe = recipe_manager.add_recipe(
                name=recipe.get('name', 'Imported Recipe'),
                ingredients=recipe.get('ingredients', []),
                instructions=recipe.get('instructions', ''),
                source=recipe.get('source', 'website'),
                source_url=recipe.get('source_url'),
                tags=data.get('tags', []),
                notes=data.get('notes', f"Imported from: {url}")
            )

            return jsonify({
                'success': True,
                'message': 'Recipe imported successfully',
                'recipe': saved_recipe
            }), 201

        # Option 2: Import from text content
        elif 'content' in data:
            content = data['content']
            recipe = extract_recipe_from_text(content)

            if not recipe:
                return jsonify({'error': 'Failed to extract recipe from content. Please provide a clearer recipe.'}), 400

            # Don't save yet - return the recipe for user to edit/confirm
            # This is the same as URL imports that need manual entry
            return jsonify({
                'success': True,
                'message': 'Recipe extracted - review before saving',
                'recipe': recipe
            }), 200

        # Option 3: Save partially extracted recipe with manual details
        elif 'save_partial' in data and data.get('save_partial'):
            recipe = data.get('recipe', {})

            # Validate we have at least a name and ingredients
            if not recipe.get('name'):
                return jsonify({'error': 'Recipe name is required'}), 400

            if not recipe.get('ingredients') or len(recipe.get('ingredients', [])) == 0:
                return jsonify({'error': 'At least one ingredient is required'}), 400

            # Save to user recipes
            saved_recipe = recipe_manager.add_recipe(
                name=recipe.get('name', 'Recipe'),
                ingredients=recipe.get('ingredients', []),
                instructions=recipe.get('instructions', ''),
                source=recipe.get('source', 'manual'),
                source_url=recipe.get('source_url'),
                tags=data.get('tags', []),
                notes=data.get('notes', f"Manually completed from: {recipe.get('source_url', 'source')}")
            )

            return jsonify({
                'success': True,
                'message': 'Recipe saved successfully',
                'recipe': saved_recipe
            }), 201

        else:
            return jsonify({'error': 'Please provide either a URL, content, or partial recipe to complete'}), 400

    except Exception as e:
        return jsonify({'error': f'Error importing recipe: {str(e)}'}), 500

# ===== Meal Planning (Monday-Friday Dinners) =====

@app.route('/api/planning', methods=['POST'])
def create_meal_plan_endpoint():
    """Create a new meal plan for Monday-Friday dinners."""
    try:
        data = request.json
        recipes_dict = data.get('recipes', {})
        week_start_date = data.get('start_date')  # YYYY-MM-DD format (Monday)

        # Validate we have all 5 days
        required_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
        if not all(day in recipes_dict for day in required_days):
            return jsonify({'error': 'Please select recipes for all 5 days (Monday-Friday)'}), 400

        # Calculate end_date if start_date is provided
        end_date = None
        if week_start_date:
            try:
                from datetime import datetime, timedelta
                start = datetime.strptime(week_start_date, '%Y-%m-%d')
                end = start + timedelta(days=4)  # Friday is 4 days after Monday
                end_date = end.strftime('%Y-%m-%d')
            except ValueError:
                return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

        # Create the meal plan with dates
        plan = PlanningManager.create_meal_plan(recipes_dict, start_date=week_start_date, end_date=end_date)

        return jsonify({
            'success': True,
            'message': 'Meal plan created successfully',
            'plan_id': plan['id'],
            'plan': plan
        }), 201

    except Exception as e:
        return jsonify({'error': f'Error creating meal plan: {str(e)}'}), 500


@app.route('/api/planning', methods=['GET'])
def get_current_plan_endpoint():
    """Get the current (most recent) meal plan."""
    try:
        plan = PlanningManager.get_current_plan()

        if not plan:
            return jsonify({
                'success': True,
                'message': 'No meal plan created yet',
                'plan': None
            }), 200

        return jsonify({
            'success': True,
            'plan': plan
        }), 200

    except Exception as e:
        return jsonify({'error': f'Error retrieving meal plan: {str(e)}'}), 500


@app.route('/api/planning/<plan_id>', methods=['DELETE'])
def delete_plan_endpoint(plan_id):
    """Delete a meal plan."""
    try:
        PlanningManager.delete_plan(plan_id)

        return jsonify({
            'success': True,
            'message': 'Meal plan deleted'
        }), 200

    except Exception as e:
        return jsonify({'error': f'Error deleting plan: {str(e)}'}), 500


@app.route('/api/planning/shopping-list', methods=['POST'])
def generate_shopping_list_from_plan():
    """Generate shopping list from a meal plan (for Saint Chris format)."""
    try:
        data = request.json
        plan_id = data.get('plan_id')
        recipes_dict = data.get('recipes')

        # Get the plan
        if plan_id:
            plan = PlanningManager.get_plan_by_id(plan_id)
        elif recipes_dict:
            # Create a temporary plan object from the recipes provided in the request
            plan = {
                'id': 'temp',
                'recipes': recipes_dict
            }
        else:
            plan = PlanningManager.get_current_plan()

        if not plan:
            return jsonify({'error': 'No meal plan found'}), 404

        # Get current inventory (optional - to exclude items already owned)
        exclude_inventory = None
        if data.get('exclude_inventory', False):
            inventory = InventoryManager.get_all_items()
            exclude_inventory = [item['name'] for item in inventory]

        # Generate shopping list
        shopping_data = PlanningManager.generate_full_shopping_list(plan, exclude_inventory)

        return jsonify({
            'success': True,
            'aggregated_ingredients': shopping_data['aggregated'],
            'ingredient_names': shopping_data['ingredient_names'],
            'csv_string': shopping_data['csv_string'],
            'total_items': shopping_data['total_items']
        }), 200

    except Exception as e:
        return jsonify({'error': f'Error generating shopping list: {str(e)}'}), 500


@app.route('/api/planning/csv', methods=['POST'])
def get_csv_export():
    """Get meal plan as CSV string (comma-separated ingredients for Saint Chris)."""
    try:
        data = request.json
        plan_id = data.get('plan_id')
        recipes_dict = data.get('recipes')

        # Get the plan
        if plan_id:
            plan = PlanningManager.get_plan_by_id(plan_id)
        elif recipes_dict:
            # Create a temporary plan object from the recipes provided in the request
            plan = {
                'id': 'temp',
                'recipes': recipes_dict
            }
        else:
            plan = PlanningManager.get_current_plan()

        if not plan:
            return jsonify({'error': 'No meal plan found'}), 404

        # Get current inventory (optional)
        exclude_inventory = None
        if data.get('exclude_inventory', False):
            inventory = InventoryManager.get_all_items()
            exclude_inventory = [item['name'] for item in inventory]

        # Generate shopping list and get CSV
        shopping_data = PlanningManager.generate_full_shopping_list(plan, exclude_inventory)

        return jsonify({
            'success': True,
            'csv_string': shopping_data['csv_string']
        }), 200

    except Exception as e:
        return jsonify({'error': f'Error generating CSV: {str(e)}'}), 500


# ===== Error Handlers =====

@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large error."""
    return jsonify({'error': 'File is too large (max 5MB)'}), 413


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def server_error(error):
    """Handle 500 errors."""
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    # Ensure data directory exists
    os.makedirs('data', exist_ok=True)
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    # Run Flask app on 0.0.0.0 to allow WiFi access
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=FLASK_DEBUG,
        threaded=True
    )
