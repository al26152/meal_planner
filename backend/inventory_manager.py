import json
import uuid
from datetime import datetime
from config import INVENTORY_FILE
import os


class InventoryManager:
    """Manage food inventory stored in JSON format."""

    @staticmethod
    def load_inventory() -> list:
        """Load inventory from JSON file."""
        try:
            if os.path.exists(INVENTORY_FILE):
                with open(INVENTORY_FILE, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            print(f"Error loading inventory: {e}")
            return []

    @staticmethod
    def save_inventory(inventory: list) -> bool:
        """Save inventory to JSON file."""
        try:
            os.makedirs(os.path.dirname(INVENTORY_FILE), exist_ok=True)
            with open(INVENTORY_FILE, 'w') as f:
                json.dump(inventory, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving inventory: {e}")
            return False

    @staticmethod
    def add_item(name: str, quantity: float, unit: str, category: str, source: str = "voice") -> dict:
        """
        Add a new item to inventory.

        Args:
            name: Food item name
            quantity: Quantity
            unit: Unit of measurement
            category: Food category
            source: Source of item (voice, receipt, etc.)

        Returns:
            The created item dict with ID and metadata
        """
        inventory = InventoryManager.load_inventory()

        item = {
            "id": str(uuid.uuid4()),
            "name": name.lower().strip(),
            "quantity": quantity,
            "unit": unit.lower().strip(),
            "category": category.lower().strip(),
            "added_date": datetime.now().isoformat(),
            "source": source,
            "notes": ""
        }

        inventory.append(item)
        InventoryManager.save_inventory(inventory)

        return item

    @staticmethod
    def add_items_batch(items: list, source: str = "voice") -> list:
        """
        Add multiple items to inventory.

        Args:
            items: List of dicts with name, quantity, unit, category
            source: Source of items

        Returns:
            List of created items
        """
        created_items = []
        for item in items:
            created_item = InventoryManager.add_item(
                name=item.get("name", ""),
                quantity=item.get("quantity", 1),
                unit=item.get("unit", "pieces"),
                category=item.get("category", "other"),
                source=source
            )
            created_items.append(created_item)

        return created_items

    @staticmethod
    def get_all_items() -> list:
        """Get all items from inventory."""
        return InventoryManager.load_inventory()

    @staticmethod
    def get_item_by_id(item_id: str) -> dict or None:
        """Get a specific item by ID."""
        inventory = InventoryManager.load_inventory()
        for item in inventory:
            if item["id"] == item_id:
                return item
        return None

    @staticmethod
    def delete_item(item_id: str) -> bool:
        """Delete an item from inventory."""
        inventory = InventoryManager.load_inventory()
        updated_inventory = [item for item in inventory if item["id"] != item_id]

        if len(updated_inventory) < len(inventory):
            InventoryManager.save_inventory(updated_inventory)
            return True

        return False

    @staticmethod
    def update_item(item_id: str, **kwargs) -> dict or None:
        """Update an item's properties."""
        inventory = InventoryManager.load_inventory()

        for item in inventory:
            if item["id"] == item_id:
                # Update allowed fields
                if "quantity" in kwargs:
                    item["quantity"] = kwargs["quantity"]
                if "unit" in kwargs:
                    item["unit"] = kwargs["unit"].lower().strip()
                if "notes" in kwargs:
                    item["notes"] = kwargs["notes"]
                if "category" in kwargs:
                    item["category"] = kwargs["category"].lower().strip()

                InventoryManager.save_inventory(inventory)
                return item

        return None

    @staticmethod
    def clear_inventory() -> bool:
        """Clear all inventory items."""
        return InventoryManager.save_inventory([])
