import json
import uuid
from datetime import datetime
from config import MEAL_PLANS_FILE
import os


class MealPlanManager:
    """Manage meal plans stored in JSON format."""

    @staticmethod
    def load_meal_plans() -> list:
        """Load meal plans from JSON file."""
        try:
            if os.path.exists(MEAL_PLANS_FILE):
                with open(MEAL_PLANS_FILE, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            print(f"Error loading meal plans: {e}")
            return []

    @staticmethod
    def save_meal_plans(meal_plans: list) -> bool:
        """Save meal plans to JSON file."""
        try:
            os.makedirs(os.path.dirname(MEAL_PLANS_FILE), exist_ok=True)
            with open(MEAL_PLANS_FILE, 'w') as f:
                json.dump(meal_plans, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving meal plans: {e}")
            return False

    @staticmethod
    def create_meal_plan(start_date: str, end_date: str, criteria: str, meals: list) -> dict:
        """
        Create a new meal plan.

        Args:
            start_date: Start date (YYYY-MM-DD format)
            end_date: End date (YYYY-MM-DD format)
            criteria: User criteria for meals (e.g., "Chinese meal", "healthy")
            meals: List of meal dicts with date and recipe info

        Returns:
            The created meal plan dict with ID and metadata
        """
        meal_plans = MealPlanManager.load_meal_plans()

        meal_plan = {
            "id": str(uuid.uuid4()),
            "start_date": start_date,
            "end_date": end_date,
            "criteria": criteria,
            "created_date": datetime.now().isoformat(),
            "meals": meals
        }

        meal_plans.append(meal_plan)
        MealPlanManager.save_meal_plans(meal_plans)

        return meal_plan

    @staticmethod
    def get_all_meal_plans() -> list:
        """Get all meal plans."""
        return MealPlanManager.load_meal_plans()

    @staticmethod
    def get_meal_plan_by_id(plan_id: str) -> dict or None:
        """Get a specific meal plan by ID."""
        meal_plans = MealPlanManager.load_meal_plans()
        for plan in meal_plans:
            if plan["id"] == plan_id:
                return plan
        return None

    @staticmethod
    def update_meal_plan(plan_id: str, **kwargs) -> dict or None:
        """Update a meal plan's properties."""
        meal_plans = MealPlanManager.load_meal_plans()

        for plan in meal_plans:
            if plan["id"] == plan_id:
                if "meals" in kwargs:
                    plan["meals"] = kwargs["meals"]
                if "criteria" in kwargs:
                    plan["criteria"] = kwargs["criteria"]

                MealPlanManager.save_meal_plans(meal_plans)
                return plan

        return None

    @staticmethod
    def update_single_meal(plan_id: str, meal_identifier: str, recipe: dict) -> dict or None:
        """Update a single meal in a plan.

        Args:
            plan_id: ID of the meal plan
            meal_identifier: Either "meal_X" format for index-based or a date string
            recipe: The new recipe dict
        """
        meal_plans = MealPlanManager.load_meal_plans()

        for plan in meal_plans:
            if plan["id"] == plan_id:
                # Handle meal_X format for index-based updates
                if meal_identifier.startswith("meal_"):
                    try:
                        meal_index = int(meal_identifier.split("_")[1])
                        if 0 <= meal_index < len(plan["meals"]):
                            plan["meals"][meal_index]["recipe"] = recipe
                            MealPlanManager.save_meal_plans(meal_plans)
                            return plan
                    except (ValueError, IndexError):
                        pass

                # Fallback to date-based lookup for backward compatibility
                for meal in plan["meals"]:
                    if meal.get("date") == meal_identifier:
                        meal["recipe"] = recipe
                        MealPlanManager.save_meal_plans(meal_plans)
                        return plan
        return None

    @staticmethod
    def delete_meal_plan(plan_id: str) -> bool:
        """Delete a meal plan."""
        meal_plans = MealPlanManager.load_meal_plans()
        updated_plans = [plan for plan in meal_plans if plan["id"] != plan_id]

        if len(updated_plans) < len(meal_plans):
            MealPlanManager.save_meal_plans(updated_plans)
            return True

        return False

    @staticmethod
    def clear_meal_plans() -> bool:
        """Clear all meal plans."""
        return MealPlanManager.save_meal_plans([])
