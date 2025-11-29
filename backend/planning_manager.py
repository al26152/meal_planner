import json
import os
from datetime import datetime
from uuid import uuid4
from collections import defaultdict

PLANNING_FILE = 'data/planning.json'


class PlanningManager:
    """Manages meal planning for the week (Monday-Friday dinners)"""

    @staticmethod
    def ensure_data_file():
        """Ensure planning data file exists"""
        os.makedirs('data', exist_ok=True)
        if not os.path.exists(PLANNING_FILE):
            with open(PLANNING_FILE, 'w') as f:
                json.dump([], f, indent=2)

    @staticmethod
    def load_plans():
        """Load all meal plans"""
        PlanningManager.ensure_data_file()
        try:
            with open(PLANNING_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []

    @staticmethod
    def save_plans(plans):
        """Save meal plans to file"""
        PlanningManager.ensure_data_file()
        with open(PLANNING_FILE, 'w') as f:
            json.dump(plans, f, indent=2)

    @staticmethod
    def create_meal_plan(recipes_dict, start_date=None, end_date=None):
        """
        Create a new meal plan for Monday-Friday.

        Args:
            recipes_dict: Dict with format {
                'monday': recipe_object,
                'tuesday': recipe_object,
                ...
                'friday': recipe_object
            }
            start_date: Optional start date (YYYY-MM-DD format, should be a Monday)
            end_date: Optional end date (YYYY-MM-DD format, should be a Friday)

        Returns:
            plan dict with id, created_date, start_date, end_date, recipes
        """
        plan = {
            'id': str(uuid4()),
            'created_date': datetime.now().isoformat(),
            'start_date': start_date,  # YYYY-MM-DD format (Monday)
            'end_date': end_date,      # YYYY-MM-DD format (Friday)
            'recipes': recipes_dict,   # Store recipe objects
            'days': list(recipes_dict.keys())  # ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
        }

        plans = PlanningManager.load_plans()
        plans.append(plan)
        PlanningManager.save_plans(plans)

        return plan

    @staticmethod
    def get_plan_by_id(plan_id):
        """Get a specific meal plan"""
        plans = PlanningManager.load_plans()
        for plan in plans:
            if plan['id'] == plan_id:
                return plan
        return None

    @staticmethod
    def get_current_plan():
        """Get the most recent meal plan (current week plan)"""
        plans = PlanningManager.load_plans()
        if plans:
            return plans[-1]  # Return latest plan
        return None

    @staticmethod
    def delete_plan(plan_id):
        """Delete a meal plan"""
        plans = PlanningManager.load_plans()
        plans = [p for p in plans if p['id'] != plan_id]
        PlanningManager.save_plans(plans)
        return True

    @staticmethod
    def aggregate_ingredients(recipes_list):
        """
        Aggregate ingredients from multiple recipes.
        Combines quantities of duplicate ingredients.

        Args:
            recipes_list: List of recipe dicts with 'ingredients' field

        Returns:
            Dict of aggregated ingredients: {
                'chicken': {'quantity': 4, 'unit': 'lbs'},
                'tomato': {'quantity': 6, 'unit': 'pieces'},
                ...
            }
        """
        aggregated = {}

        for recipe in recipes_list:
            if not recipe or not recipe.get('ingredients'):
                continue

            ingredients = recipe.get('ingredients', [])

            # Handle both list of dicts and list of strings
            for ingredient in ingredients:
                if isinstance(ingredient, dict):
                    # Format: {'name': 'chicken', 'quantity': 2, 'unit': 'lbs'}
                    name = ingredient.get('name', '').lower().strip()
                    quantity = ingredient.get('quantity', 1)
                    unit = ingredient.get('unit', 'pieces')

                    if not name:
                        continue

                    # Try to convert quantity to float
                    try:
                        quantity = float(quantity)
                    except (ValueError, TypeError):
                        quantity = 1

                    # Aggregate
                    if name in aggregated:
                        # Add to existing quantity if same unit
                        if aggregated[name]['unit'] == unit:
                            aggregated[name]['quantity'] += quantity
                        else:
                            # Different units, keep separate
                            name = f"{name} ({unit})"
                            aggregated[name] = {'quantity': quantity, 'unit': unit}
                    else:
                        aggregated[name] = {'quantity': quantity, 'unit': unit}

                elif isinstance(ingredient, str):
                    # Format: "2 lbs chicken" or just "chicken"
                    ingredient_name = ingredient.lower().strip()
                    if ingredient_name:
                        if ingredient_name in aggregated:
                            aggregated[ingredient_name]['quantity'] += 1
                        else:
                            aggregated[ingredient_name] = {'quantity': 1, 'unit': 'pieces'}

        return aggregated

    @staticmethod
    def get_shopping_ingredients(recipes_list, exclude_inventory=None):
        """
        Get aggregated shopping ingredients from recipes.
        Optionally exclude items already in inventory.

        Args:
            recipes_list: List of recipe dicts
            exclude_inventory: Optional list of inventory item names to exclude

        Returns:
            List of ingredient names (without quantities/units)
        """
        aggregated = PlanningManager.aggregate_ingredients(recipes_list)

        ingredient_names = []
        for name, details in aggregated.items():
            # Check if we should exclude this ingredient
            if exclude_inventory:
                # Simple check - if ingredient name is in inventory
                should_exclude = any(
                    inv_name.lower() in name.lower() or name.lower() in inv_name.lower()
                    for inv_name in exclude_inventory
                )
                if not should_exclude:
                    ingredient_names.append(name)
            else:
                ingredient_names.append(name)

        return sorted(ingredient_names)

    @staticmethod
    def get_csv_string(ingredient_names):
        """
        Convert ingredient list to CSV format (comma-separated, no volumes).

        Args:
            ingredient_names: List of ingredient names

        Returns:
            Comma-separated string: "chicken, tomatoes, basil, milk"
        """
        if not ingredient_names:
            return ""

        # Join with comma and space
        csv_string = ", ".join(ingredient_names)
        return csv_string

    @staticmethod
    def generate_full_shopping_list(plan, exclude_inventory=None):
        """
        Generate complete shopping list from a meal plan.

        Args:
            plan: Meal plan dict with recipes
            exclude_inventory: Optional list of inventory items to exclude

        Returns:
            Dict with:
            - aggregated: aggregated ingredients with quantities
            - ingredient_names: list of ingredient names only
            - csv_string: comma-separated string for Saint Chris
        """
        recipes_list = list(plan.get('recipes', {}).values())

        aggregated = PlanningManager.aggregate_ingredients(recipes_list)
        ingredient_names = PlanningManager.get_shopping_ingredients(recipes_list, exclude_inventory)
        csv_string = PlanningManager.get_csv_string(ingredient_names)

        return {
            'aggregated': aggregated,
            'ingredient_names': ingredient_names,
            'csv_string': csv_string,
            'total_items': len(ingredient_names)
        }
