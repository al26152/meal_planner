from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import os
from config import FLASK_DEBUG, FLASK_ENV, UPLOAD_FOLDER, MAX_FILE_SIZE, ALLOWED_EXTENSIONS
from backend.transcription_processor import process_transcription_file
from backend.receipt_handler import process_receipt_file, save_uploaded_file as save_receipt_file
from backend.inventory_manager import InventoryManager
from backend.meal_plan_manager import MealPlanManager
from backend.recipe_generator import generate_meal_plan, generate_unified_meal_plan, regenerate_single_meal, get_suggested_recipes, search_recipes_by_type
from backend.openai_client import suggest_recipe_types
from backend.shopping_list_generator import generate_shopping_list

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


# ===== Meal Planning Routes =====

@app.route('/api/meal-plans/generate', methods=['POST'])
def generate_meal_plan_endpoint():
    """Generate a new meal plan."""
    try:
        data = request.json
        num_meals = data.get('num_meals')
        criteria = data.get('criteria', '')

        if not num_meals:
            return jsonify({'error': 'num_meals is required'}), 400

        # Get current inventory
        inventory = InventoryManager.get_all_items()

        # Generate unified meal plan (AI + API + Curation)
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
            'message': f'Generated {result.get("count")} delicious meals',
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


@app.route('/api/recipes/suggest-types', methods=['GET'])
def suggest_recipe_types_endpoint():
    """Get AI-suggested recipe types based on current inventory."""
    try:
        # Get current inventory
        inventory = InventoryManager.get_all_items()

        if not inventory:
            return jsonify({'error': 'No inventory items available'}), 400

        # Get recipe type suggestions from AI
        suggestions = suggest_recipe_types(inventory)

        if not suggestions:
            return jsonify({'error': 'Could not generate recipe suggestions'}), 400

        return jsonify({
            'success': True,
            'count': len(suggestions),
            'suggestions': suggestions
        }), 200

    except Exception as e:
        return jsonify({'error': f'Error getting recipe suggestions: {str(e)}'}), 500


@app.route('/api/recipes/search', methods=['POST'])
def search_recipes():
    """Search for recipes by type with inventory matching."""
    try:
        data = request.json
        recipe_type = data.get('recipe_type')

        if not recipe_type:
            return jsonify({'error': 'recipe_type is required'}), 400

        # Get current inventory
        inventory = InventoryManager.get_all_items()

        if not inventory:
            return jsonify({'error': 'No inventory items available'}), 400

        # Search recipes matching the type
        result = search_recipes_by_type(inventory, recipe_type, num_results=5)

        if not result.get('success'):
            return jsonify({'error': result.get('error', 'Failed to search recipes')}), 400

        return jsonify({
            'success': True,
            'count': result.get('count'),
            'recipe_type': result.get('recipe_type'),
            'source': result.get('source'),
            'recipes': result.get('recipes', [])
        }), 200

    except Exception as e:
        return jsonify({'error': f'Error searching recipes: {str(e)}'}), 500


@app.route('/api/recipes/suggestions', methods=['GET'])
def get_recipe_suggestions():
    """Get recipe suggestions based on current inventory from API Ninjas."""
    try:
        # Get optional parameters
        num_suggestions = request.args.get('limit', 5, type=int)

        # Get current inventory
        inventory = InventoryManager.get_all_items()

        if not inventory:
            return jsonify({'error': 'No inventory items available for recipe suggestions'}), 400

        # Get suggested recipes from API Ninjas
        result = get_suggested_recipes(inventory, num_suggestions)

        if not result.get('success'):
            return jsonify({'error': result.get('error', 'Failed to get recipe suggestions')}), 400

        return jsonify({
            'success': True,
            'count': result.get('count'),
            'source': result.get('source'),
            'recipes': result.get('recipes', [])
        }), 200

    except Exception as e:
        return jsonify({'error': f'Error getting recipe suggestions: {str(e)}'}), 500


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
