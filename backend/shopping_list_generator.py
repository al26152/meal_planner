"""Generate shopping lists based on meal plans and current inventory."""


def generate_shopping_list(meal_plan: dict, inventory: list) -> dict:
    """
    Generate a shopping list of missing ingredients for a meal plan.

    Args:
        meal_plan: Meal plan dict with meals list
        inventory: Current inventory items

    Returns:
        Dict with shopping list grouped by category and missing items
    """

    # Create inventory lookup by name (normalized)
    inventory_lookup = {}
    for item in inventory:
        key = _normalize_ingredient_name(item.get("name", ""))
        if key:
            inventory_lookup[key] = {
                "quantity": item.get("quantity", 0),
                "unit": item.get("unit", "pieces"),
                "category": item.get("category", "other")
            }

    # Aggregate all recipe ingredients
    ingredient_needs = {}  # {normalized_name: {quantity, unit, category, in_recipes}}

    meals = meal_plan.get("meals", [])
    for meal in meals:
        recipe = meal.get("recipe", {})
        ingredients = recipe.get("ingredients", [])

        for ing in ingredients:
            ing_name = ing.get("name", "")
            normalized = _normalize_ingredient_name(ing_name)

            if not normalized:
                continue

            qty = float(ing.get("quantity", 1))
            unit = ing.get("unit", "pieces")

            if normalized not in ingredient_needs:
                ingredient_needs[normalized] = {
                    "name": ing_name,
                    "quantity_needed": qty,
                    "unit": unit,
                    "in_recipes": 1,
                    "category": "other"
                }
            else:
                # Accumulate quantities (simplified - assumes same unit)
                ingredient_needs[normalized]["quantity_needed"] += qty
                ingredient_needs[normalized]["in_recipes"] += 1

    # Calculate what's missing
    shopping_list = []
    categories = {}

    for normalized_name, need in ingredient_needs.items():
        have = inventory_lookup.get(normalized_name, {})
        have_qty = have.get("quantity", 0)
        category = have.get("category", "other")
        need["category"] = category

        missing_qty = need["quantity_needed"] - have_qty

        if missing_qty > 0:
            missing_item = {
                "name": need["name"],
                "quantity_needed": need["quantity_needed"],
                "quantity_have": have_qty,
                "quantity_missing": missing_qty,
                "unit": need["unit"],
                "category": category,
                "in_recipes": need["in_recipes"]
            }

            shopping_list.append(missing_item)

            # Group by category
            if category not in categories:
                categories[category] = []
            categories[category].append(missing_item)

    # Sort by category and name
    sorted_categories = {}
    for cat in sorted(categories.keys()):
        sorted_categories[cat] = sorted(
            categories[cat],
            key=lambda x: x["name"]
        )

    return {
        "success": True,
        "total_missing_items": len(shopping_list),
        "shopping_list": shopping_list,
        "by_category": sorted_categories
    }


def _normalize_ingredient_name(name: str) -> str:
    """Normalize ingredient name for comparison."""
    if not name:
        return ""
    # Remove common units and words, lowercase, strip
    normalized = name.lower().strip()
    # Remove articles and common words
    words_to_remove = ["the ", "a ", "some ", "fresh ", "frozen "]
    for word in words_to_remove:
        normalized = normalized.replace(word, "")
    return normalized.strip()
