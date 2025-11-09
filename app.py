from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import os
from config import FLASK_DEBUG, FLASK_ENV, UPLOAD_FOLDER, MAX_FILE_SIZE, ALLOWED_EXTENSIONS
from backend.transcription_processor import process_transcription_file
from backend.receipt_handler import process_receipt_file, save_uploaded_file as save_receipt_file
from backend.inventory_manager import InventoryManager

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
