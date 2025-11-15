import json
import os
from uuid import uuid4
from datetime import datetime


class ShoppingListManager:
    """Manages shopping list for recipes with missing ingredients."""

    SHOPPING_LIST_FILE = 'data/shopping_list.json'

    @staticmethod
    def _ensure_file_exists():
        """Ensure shopping list file exists."""
        os.makedirs('data', exist_ok=True)
        if not os.path.exists(ShoppingListManager.SHOPPING_LIST_FILE):
            with open(ShoppingListManager.SHOPPING_LIST_FILE, 'w') as f:
                json.dump([], f)

    @staticmethod
    def load_shopping_list():
        """Load all shopping list items."""
        ShoppingListManager._ensure_file_exists()
        try:
            with open(ShoppingListManager.SHOPPING_LIST_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []

    @staticmethod
    def save_shopping_list(items):
        """Save shopping list items to file."""
        ShoppingListManager._ensure_file_exists()
        with open(ShoppingListManager.SHOPPING_LIST_FILE, 'w') as f:
            json.dump(items, f, indent=2)

    @staticmethod
    def add_item(name, quantity=1, unit='', notes=''):
        """Add item to shopping list."""
        items = ShoppingListManager.load_shopping_list()

        # Check if item already exists (case-insensitive)
        existing = next(
            (item for item in items if item['name'].lower() == name.lower()),
            None
        )

        if existing:
            # Update quantity if exists
            existing['quantity'] += quantity
            existing['updated_date'] = datetime.now().isoformat()
        else:
            # Add new item
            new_item = {
                'id': str(uuid4()),
                'name': name,
                'quantity': quantity,
                'unit': unit,
                'notes': notes,
                'added_date': datetime.now().isoformat(),
                'updated_date': datetime.now().isoformat(),
                'completed': False
            }
            items.append(new_item)

        ShoppingListManager.save_shopping_list(items)
        return items

    @staticmethod
    def add_items_batch(items_list):
        """Add multiple items to shopping list at once."""
        shopping_list = ShoppingListManager.load_shopping_list()

        for item in items_list:
            name = item.get('name', '').strip()
            if not name:
                continue

            # Check if exists
            existing = next(
                (i for i in shopping_list if i['name'].lower() == name.lower()),
                None
            )

            if existing:
                existing['quantity'] += item.get('quantity', 1)
                existing['updated_date'] = datetime.now().isoformat()
            else:
                new_item = {
                    'id': str(uuid4()),
                    'name': name,
                    'quantity': item.get('quantity', 1),
                    'unit': item.get('unit', ''),
                    'notes': item.get('notes', ''),
                    'added_date': datetime.now().isoformat(),
                    'updated_date': datetime.now().isoformat(),
                    'completed': False
                }
                shopping_list.append(new_item)

        ShoppingListManager.save_shopping_list(shopping_list)
        return shopping_list

    @staticmethod
    def get_item(item_id):
        """Get shopping list item by ID."""
        items = ShoppingListManager.load_shopping_list()
        return next((item for item in items if item['id'] == item_id), None)

    @staticmethod
    def update_item(item_id, **kwargs):
        """Update shopping list item."""
        items = ShoppingListManager.load_shopping_list()
        item = next((i for i in items if i['id'] == item_id), None)

        if item:
            for key, value in kwargs.items():
                if key in item:
                    item[key] = value
            item['updated_date'] = datetime.now().isoformat()
            ShoppingListManager.save_shopping_list(items)
            return item

        return None

    @staticmethod
    def toggle_item(item_id):
        """Toggle item completed status."""
        items = ShoppingListManager.load_shopping_list()
        item = next((i for i in items if i['id'] == item_id), None)

        if item:
            item['completed'] = not item['completed']
            item['updated_date'] = datetime.now().isoformat()
            ShoppingListManager.save_shopping_list(items)
            return item

        return None

    @staticmethod
    def delete_item(item_id):
        """Remove item from shopping list."""
        items = ShoppingListManager.load_shopping_list()
        items = [item for item in items if item['id'] != item_id]
        ShoppingListManager.save_shopping_list(items)
        return True

    @staticmethod
    def clear_shopping_list():
        """Clear all items from shopping list."""
        ShoppingListManager.save_shopping_list([])
        return True

    @staticmethod
    def get_active_items():
        """Get non-completed items sorted by most recent."""
        items = ShoppingListManager.load_shopping_list()
        active = [item for item in items if not item.get('completed', False)]
        return sorted(active, key=lambda x: x.get('updated_date', ''), reverse=True)

    @staticmethod
    def get_completed_items():
        """Get completed items."""
        items = ShoppingListManager.load_shopping_list()
        return [item for item in items if item.get('completed', False)]
