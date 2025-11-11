import json
import requests
from datetime import datetime, timedelta
from openai import OpenAI
from config import OPENAI_API_KEY, API_NINJAS_KEY
import os

client = OpenAI(api_key=OPENAI_API_KEY)


def _load_preferences() -> dict:
    """Load user preferences from JSON file."""
    prefs_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "user_preferences.json")

    try:
        if os.path.exists(prefs_path):
            with open(prefs_path, 'r') as f:
                data = json.load(f)
                return data.get("user_preferences", {})
    except Exception as e:
        print(f"Error loading preferences: {e}")

    return {}


def _format_preferences_for_prompt(preferences: dict) -> str:
    """Format preferences into a readable prompt section."""
    if not preferences:
        return ""

    lines = ["USER PREFERENCES:"]

    if preferences.get("dietary_restrictions"):
        lines.append(f"- Dietary Restrictions: {', '.join(preferences['dietary_restrictions'])}")

    if preferences.get("cuisine_types"):
        lines.append(f"- Preferred Cuisines: {', '.join(preferences['cuisine_types'])}")

    if preferences.get("meal_types"):
        lines.append(f"- Meal Types: {', '.join(preferences['meal_types'])}")

    if preferences.get("cooking_time"):
        lines.append(f"- Cooking Time: {', '.join(preferences['cooking_time'])}")

    if preferences.get("nutritional_goals"):
        lines.append(f"- Nutritional Goals: {', '.join(preferences['nutritional_goals'])}")

    if preferences.get("equipment"):
        lines.append(f"- Available Equipment: {', '.join(preferences['equipment'])}")

    exclude_ingredients = preferences.get("ingredient_preferences", {}).get("exclude", [])
    if exclude_ingredients:
        lines.append(f"- Ingredients to Avoid: {', '.join(exclude_ingredients)}")

    return "\n".join(lines)


def generate_meal_plan(num_meals: int, criteria: str, inventory: list) -> dict:
    """
    Generate meal recipes using available inventory.

    Args:
        num_meals: Number of meals to generate
        criteria: User criteria (e.g., "Italian", "healthy", "vegetarian", "gourmet")
        inventory: List of available inventory items with name, quantity, unit, category

    Returns:
        Dict with success status and meals list, or error message
    """

    if num_meals < 1 or num_meals > 30:
        return {"success": False, "error": "Number of meals must be between 1 and 30"}

    # Load user preferences
    preferences = _load_preferences()
    preferences_text = _format_preferences_for_prompt(preferences)

    # Format inventory for the prompt
    inventory_text = _format_inventory_for_prompt(inventory)

    # Create prompt for meal planning - focused on creating gourmet, sophisticated recipes
    prompt = f"""You are a professional chef and meal planning expert. Generate {num_meals} delicious, sophisticated dinner recipes.

Style/Preferences: {criteria}

{preferences_text}

Available ingredients to use:
{inventory_text}

Requirements:
1. Create delicious, restaurant-quality recipes
2. Each recipe should be interesting and engaging
3. Match the style/preferences: {criteria}
4. Use ingredients from the available inventory
5. Include realistic cooking instructions with time estimates
6. Make recipes feel special and worth making

Return ONLY a valid JSON array where each element has:
{{
  "recipe": {{
    "name": "creative recipe name",
    "ingredients": [
      {{"name": "ingredient", "quantity": number, "unit": "measurement"}}
    ],
    "instructions": "detailed step-by-step cooking instructions with tips"
  }}
}}

Do not include any other text. Return only the JSON array with {num_meals} recipes."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a meal planning assistant. Generate practical dinner recipes based on available inventory and user preferences. Return only valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,  # Higher temperature for creativity in meal planning
            max_tokens=3000
        )

        response_text = response.choices[0].message.content.strip()

        # Handle markdown code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        meals = json.loads(response_text)

        if not isinstance(meals, list):
            return {"success": False, "error": "Invalid response format"}

        # Validate meals
        validated_meals = []
        for index, meal in enumerate(meals):
            if isinstance(meal, dict) and "recipe" in meal:
                validated_meal = {
                    "recipe": {
                        "name": str(meal["recipe"].get("name", "Unknown Recipe")).strip(),
                        "ingredients": _validate_ingredients(meal["recipe"].get("ingredients", [])),
                        "instructions": str(meal["recipe"].get("instructions", "")).strip()
                    }
                }
                if validated_meal["recipe"]["name"]:
                    validated_meals.append(validated_meal)

        return {
            "success": True,
            "count": len(validated_meals),
            "meals": validated_meals
        }

    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Error parsing OpenAI response: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Error generating meal plan: {str(e)}"}


def regenerate_single_meal(meal_index: int, criteria: str, inventory: list) -> dict:
    """
    Regenerate a single meal with new criteria.

    Args:
        meal_index: Index of the meal to regenerate (0-based)
        criteria: User criteria for the meal (e.g., "Italian", "healthy", "gourmet")
        inventory: List of available inventory items

    Returns:
        Dict with success status and recipe, or error message
    """

    # Load user preferences
    preferences = _load_preferences()
    preferences_text = _format_preferences_for_prompt(preferences)

    inventory_text = _format_inventory_for_prompt(inventory)

    prompt = f"""You are a professional chef. Generate ONE sophisticated, delicious dinner recipe with these preferences: {criteria}

{preferences_text}

Available ingredients:
{inventory_text}

Create a gourmet dinner recipe that:
1. Uses ingredients from the available inventory
2. Matches the style/preferences: {criteria}
3. Is interesting and worth cooking
4. Includes detailed instructions with cooking tips

Return ONLY a valid JSON object:
{{
  "name": "creative recipe name",
  "ingredients": [
    {{"name": "ingredient", "quantity": number, "unit": "measurement"}}
  ],
  "instructions": "detailed step-by-step cooking instructions with tips"
}}

Do not include any other text. Return only the JSON object."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a meal planning assistant. Generate a practical dinner recipe based on available inventory and user preferences. Return only valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=1500
        )

        response_text = response.choices[0].message.content.strip()

        # Handle markdown code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        recipe = json.loads(response_text)

        # Validate recipe
        if isinstance(recipe, dict) and "name" in recipe:
            validated_recipe = {
                "name": str(recipe.get("name", "Unknown Recipe")).strip(),
                "ingredients": _validate_ingredients(recipe.get("ingredients", [])),
                "instructions": str(recipe.get("instructions", "")).strip()
            }
            if validated_recipe["name"]:
                return {
                    "success": True,
                    "recipe": validated_recipe
                }

        return {"success": False, "error": "Invalid recipe format"}

    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Error parsing response: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Error regenerating meal: {str(e)}"}


def _format_inventory_for_prompt(inventory: list) -> str:
    """Format inventory list for inclusion in prompt."""
    if not inventory:
        return "No items available"

    inventory_lines = []
    for item in inventory:
        name = item.get("name", "unknown")
        qty = item.get("quantity", 0)
        unit = item.get("unit", "pieces")
        inventory_lines.append(f"- {name}: {qty} {unit}")

    return "\n".join(inventory_lines)


def _validate_ingredients(ingredients: list) -> list:
    """Validate and normalize ingredients list."""
    validated = []
    for ing in ingredients:
        if isinstance(ing, dict) and "name" in ing:
            validated_ing = {
                "name": str(ing.get("name", "")).lower().strip(),
                "quantity": float(ing.get("quantity", 1)),
                "unit": str(ing.get("unit", "pieces")).lower().strip()
            }
            if validated_ing["name"]:
                validated.append(validated_ing)
    return validated


def _generate_ingredient_combinations(ingredients: list, min_target: int, max_target: int) -> list:
    """
    Generate combinations of ingredients within the target range (40-50%).
    Falls back to single ingredients if needed.

    Args:
        ingredients: List of all available ingredients
        min_target: Minimum number of ingredients per combination
        max_target: Maximum number of ingredients per combination

    Returns:
        List of ingredient combinations to search for
    """
    from itertools import combinations
    import random

    combinations_list = []

    # Generate combinations starting with the most promising sizes
    for size in range(max_target, min_target - 1, -1):
        # Limit combinations to avoid too many API calls
        all_combos = list(combinations(ingredients, size))
        max_combos = min(5, len(all_combos))

        # Randomly sample combinations if there are many
        if max_combos < len(all_combos):
            sampled = random.sample(all_combos, max_combos)
        else:
            sampled = all_combos

        for combo in sampled:
            combinations_list.append(list(combo))

    # Also add individual ingredients as fallback (representing more specific searches)
    for ingredient in ingredients[:10]:  # Limit to first 10 ingredients
        combinations_list.append([ingredient])

    return combinations_list


def search_recipes_by_type(inventory: list, recipe_type: str, num_results: int = 5) -> dict:
    """
    Search for recipes of a specific type that match inventory ingredients.
    Returns recipes with tracking of which ingredients user has vs needs to buy.

    Args:
        inventory: List of available inventory items
        recipe_type: Type of recipe to search for (e.g., "Italian Pasta", "Thai Curry")
        num_results: Number of recipes to return (default: 5)

    Returns:
        Dict with success status and recipes with ingredient matching info
    """

    if not inventory:
        return {"success": False, "error": "No inventory items available"}

    if not recipe_type or not recipe_type.strip():
        return {"success": False, "error": "Recipe type is required"}

    # Extract inventory ingredient names (normalized)
    inventory_items = {item.get("name", "").lower().strip() for item in inventory if item.get("name")}

    try:
        headers = {"X-Api-Key": API_NINJAS_KEY}
        recipes_data = []
        seen_recipes = set()

        # Search for recipes matching the type
        params = {"ingredients": recipe_type}

        try:
            response = requests.get(
                "https://api.api-ninjas.com/v2/recipe",
                headers=headers,
                params=params,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                recipes_data.extend(data)
        except Exception as e:
            print(f"Error searching for {recipe_type}: {e}")

        if not recipes_data:
            return {"success": False, "error": f"No recipes found for {recipe_type}"}

        # Process recipes and match against inventory
        formatted_recipes = []

        for recipe in recipes_data[:num_results]:
            recipe_title = recipe.get("title", "")
            if recipe_title in seen_recipes:
                continue
            seen_recipes.add(recipe_title)

            # Parse recipe ingredients and match against inventory
            recipe_ingredients = recipe.get("ingredients", [])
            if isinstance(recipe_ingredients, list):
                ingredient_list = recipe_ingredients
            else:
                ingredient_list = []

            # Match ingredients
            has_ingredients = []
            missing_ingredients = []

            for ingredient in ingredient_list:
                ingredient_name = str(ingredient).lower().strip()
                # Simple matching - check if any inventory item is in the ingredient name
                found = False
                for inv_item in inventory_items:
                    if inv_item in ingredient_name or ingredient_name in inv_item:
                        has_ingredients.append(ingredient)
                        found = True
                        break
                if not found:
                    missing_ingredients.append(ingredient)

            # Calculate match percentage
            total_ingredients = len(ingredient_list)
            match_percentage = (len(has_ingredients) / total_ingredients * 100) if total_ingredients > 0 else 0

            formatted_recipe = {
                "name": recipe_title,
                "servings": recipe.get("servings", "Not specified"),
                "ingredients": _format_api_ingredients(recipe.get("ingredients", [])),
                "instructions": recipe.get("instructions", "No instructions provided"),
                "match_percentage": round(match_percentage, 1),
                "has_ingredients": has_ingredients,
                "missing_ingredients": missing_ingredients,
                "total_ingredients": total_ingredients
            }
            formatted_recipes.append(formatted_recipe)

        # Sort by match percentage (highest first)
        formatted_recipes.sort(key=lambda x: x['match_percentage'], reverse=True)

        return {
            "success": True,
            "count": len(formatted_recipes),
            "recipe_type": recipe_type,
            "source": "API Ninjas",
            "recipes": formatted_recipes
        }

    except requests.exceptions.Timeout:
        return {"success": False, "error": "API request timed out"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Error fetching recipes: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Error processing recipes: {str(e)}"}


def get_suggested_recipes(inventory: list, num_suggestions: int = 5) -> dict:
    """
    Get recipe suggestions from API Ninjas based on available inventory ingredients.

    Args:
        inventory: List of available inventory items with name, quantity, unit, category
        num_suggestions: Number of recipe suggestions to retrieve (default: 5, max varies by subscription)

    Returns:
        Dict with success status and recipes list, or error message
    """

    if num_suggestions < 1:
        return {"success": False, "error": "Number of suggestions must be at least 1"}

    if not inventory:
        return {"success": False, "error": "No inventory items available for recipe suggestions"}

    # Extract ingredient names from inventory
    ingredients = [item.get("name", "").strip() for item in inventory if item.get("name")]

    if not ingredients:
        return {"success": False, "error": "No valid ingredients found in inventory"}

    try:
        headers = {"X-Api-Key": API_NINJAS_KEY}
        recipes_data = []
        seen_recipes = set()  # Track recipes to avoid duplicates

        # Calculate target ingredient count (40-50% of available ingredients)
        total_ingredients = len(ingredients)
        min_target = max(1, int(total_ingredients * 0.4))
        max_target = max(min_target + 1, int(total_ingredients * 0.5))

        # Generate ingredient combinations in the 40-50% range
        ingredient_combinations = _generate_ingredient_combinations(ingredients, min_target, max_target)

        # Search for recipes using each combination
        for combo in ingredient_combinations:
            if len(recipes_data) >= num_suggestions:
                break

            ingredients_str = ", ".join(combo)
            params = {"ingredients": ingredients_str}

            try:
                response = requests.get(
                    "https://api.api-ninjas.com/v2/recipe",
                    headers=headers,
                    params=params,
                    timeout=10
                )

                if response.status_code == 200:
                    data = response.json()
                    for recipe in data:
                        recipe_title = recipe.get("title", "")
                        if recipe_title not in seen_recipes:
                            recipes_data.append(recipe)
                            seen_recipes.add(recipe_title)
                            if len(recipes_data) >= num_suggestions:
                                break
            except Exception:
                continue  # Skip this combination if there's an error

        if not recipes_data:
            return {"success": False, "error": "No recipes found for the given ingredients"}

        # Format recipes for consistent output
        formatted_recipes = []
        for recipe in recipes_data[:num_suggestions]:
            formatted_recipe = {
                "name": recipe.get("title", "Unknown Recipe"),
                "ingredients": _format_api_ingredients(recipe.get("ingredients", [])),
                "instructions": recipe.get("instructions", "No instructions provided"),
                "servings": recipe.get("servings", "Not specified")
            }
            formatted_recipes.append(formatted_recipe)

        return {
            "success": True,
            "count": len(formatted_recipes),
            "source": "API Ninjas",
            "recipes": formatted_recipes
        }

    except requests.exceptions.Timeout:
        return {"success": False, "error": "API request timed out"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Error fetching recipes: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Error processing recipe suggestions: {str(e)}"}


def _format_api_ingredients(ingredients_data) -> list:
    """
    Parse ingredients from API response into structured format.

    Args:
        ingredients_data: Raw ingredients from API (can be list or string)

    Returns:
        List of formatted ingredient dictionaries
    """

    if not ingredients_data:
        return []

    formatted = []

    # Handle list of ingredients (standard API response)
    if isinstance(ingredients_data, list):
        for ingredient in ingredients_data:
            if ingredient:
                formatted.append({
                    "name": str(ingredient).strip(),
                    "quantity": 1,
                    "unit": "as needed"
                })
    # Handle string format (fallback)
    elif isinstance(ingredients_data, str):
        ingredient_lines = ingredients_data.split("|") if "|" in ingredients_data else [ingredients_data]
        for ingredient_line in ingredient_lines:
            ingredient_line = ingredient_line.strip()
            if ingredient_line:
                formatted.append({
                    "name": ingredient_line,
                    "quantity": 1,
                    "unit": "as needed"
                })

    return formatted
