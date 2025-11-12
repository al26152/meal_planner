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
            max_tokens=3000,
            timeout=60.0  # 60 second timeout
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
            max_tokens=1500,
            timeout=60.0  # 60 second timeout
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
    Uses random sampling to avoid memory exhaustion.

    Args:
        ingredients: List of all available ingredients
        min_target: Minimum number of ingredients per combination
        max_target: Maximum number of ingredients per combination

    Returns:
        List of ingredient combinations to search for
    """
    from itertools import combinations
    import random
    from math import comb

    combinations_list = []

    # Generate combinations starting with the most promising sizes
    for size in range(max_target, min_target - 1, -1):
        # Calculate total combinations WITHOUT generating them
        total_combos = comb(len(ingredients), size)

        # Limit to 5 samples per size to avoid API call overload
        max_samples = 5

        # Use random sampling without generating all combinations
        # This prevents memory exhaustion with large ingredient lists
        if total_combos <= max_samples:
            # Small number - generate all combinations
            sampled = list(combinations(ingredients, size))
        else:
            # Large number - random sample directly
            sampled = []
            for _ in range(max_samples):
                # Randomly select 'size' ingredients without replacement
                sampled_ingredients = random.sample(ingredients, size)
                sampled.append(tuple(sampled_ingredients))

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


def generate_unified_meal_plan(num_meals: int, criteria: str, inventory: list) -> dict:
    """
    Unified meal planning: Combine AI-generated recipes with API recipes and curate them.

    This is the main orchestration function that:
    1. Generates 2-3 AI recipes
    2. Fetches 5-10 API recipes
    3. Uses AI to curate and combine them
    4. Returns a balanced meal plan with mixed sources

    Args:
        num_meals: Number of final meals to return (1-30)
        criteria: User criteria/preferences (e.g., "Italian", "healthy", "vegetarian")
        inventory: List of available inventory items

    Returns:
        Dict with success status and curated meals list
    """

    if num_meals < 1 or num_meals > 30:
        return {"success": False, "error": "Number of meals must be between 1 and 30"}

    # Load user preferences
    preferences = _load_preferences()

    try:
        # Step 1: Generate AI recipes (2-3)
        ai_num = min(3, max(1, num_meals // 2))  # 1-3 recipes
        ai_result = generate_meal_plan(ai_num, criteria, inventory)

        if not ai_result.get("success"):
            return {"success": False, "error": "Failed to generate AI recipes: " + ai_result.get("error", "Unknown error")}

        ai_recipes = ai_result.get("meals", [])
        print(f"Generated {len(ai_recipes)} AI recipes")

        # Step 2: Fetch API recipes (5-10)
        api_num = min(10, max(5, num_meals))
        api_result = get_suggested_recipes(inventory, api_num)

        if not api_result.get("success"):
            # If API fails, just use AI recipes
            print(f"API recipe fetch failed: {api_result.get('error')}, using AI recipes only")
            api_recipes = []
        else:
            api_recipes = api_result.get("recipes", [])
            print(f"Fetched {len(api_recipes)} API recipes")

        # Step 3: Curate and combine using AI
        from backend.recipe_curator import curate_recipes_with_ai

        curated_recipes = curate_recipes_with_ai(ai_recipes, api_recipes, num_meals, preferences)
        print(f"Curated down to {len(curated_recipes)} final recipes")

        # Step 4: Convert to meal plan format (wrap in "recipe" key for consistency)
        meals = []
        for i, recipe in enumerate(curated_recipes):
            # Handle both AI and API recipe formats
            if "recipe" in recipe:  # AI format
                meal = {"recipe": recipe["recipe"]}
            else:  # API or curated format
                meal = {
                    "recipe": {
                        "name": recipe.get("name", "Unknown Recipe"),
                        "ingredients": recipe.get("ingredients", recipe.get("main_ingredients", [])),
                        "instructions": recipe.get("instructions", ""),
                        "source": recipe.get("source", "Unknown")
                    }
                }
            meals.append(meal)

        return {
            "success": True,
            "count": len(meals),
            "meals": meals,
            "message": f"Generated {len(meals)} curated meals from AI + API sources"
        }

    except Exception as e:
        print(f"Error in unified meal planning: {e}")
        return {"success": False, "error": f"Error generating unified meal plan: {str(e)}"}


def generate_meal_plan_with_curated(num_meals: int, criteria: str, inventory: list,
                                   use_curated_first: bool = True) -> dict:
    """
    Enhanced meal planning with user-curated recipes as primary source.

    Prioritizes user-curated recipes, adapts them to inventory, then supplements with AI/API.

    This is the enhanced orchestration function that:
    1. Fetches and adapts user-curated recipes
    2. Optionally generates AI recipes
    3. Optionally fetches API recipes
    4. Curates all sources together
    5. Returns a balanced meal plan prioritizing curated recipes

    Args:
        num_meals: Number of final meals to return (1-30)
        criteria: User criteria/preferences (e.g., "Italian", "healthy", "vegetarian")
        inventory: List of available inventory items
        use_curated_first: If True, prioritize curated recipes (default True)

    Returns:
        Dict with success status and curated meals list
    """
    from backend.user_recipe_manager import UserRecipeManager
    from backend.openai_client import adapt_recipe_to_inventory

    if num_meals < 1 or num_meals > 30:
        return {"success": False, "error": "Number of meals must be between 1 and 30"}

    # Load user preferences
    preferences = _load_preferences()
    recipe_manager = UserRecipeManager('data')

    try:
        all_sources = []

        # Step 1: Get and adapt user-curated recipes
        curated_recipes = recipe_manager.get_all_recipes()

        if curated_recipes:
            print(f"Found {len(curated_recipes)} user-curated recipes")

            # Filter by criteria if provided (simple name/tag matching)
            if criteria:
                criteria_lower = criteria.lower()
                filtered = []
                for recipe in curated_recipes:
                    # Check if criteria matches recipe name, tags, or cuisine
                    name_match = criteria_lower in recipe.get('name', '').lower()
                    tags_match = any(criteria_lower in tag.lower() for tag in recipe.get('tags', []))
                    cuisine_match = criteria_lower in recipe.get('cuisine', '').lower() if recipe.get('cuisine') else False

                    if name_match or tags_match or cuisine_match:
                        filtered.append(recipe)

                # If no matches found, use all curated recipes
                if filtered:
                    curated_recipes = filtered

            print(f"Using {len(curated_recipes)} curated recipes after filtering")

            # Adapt each curated recipe to available inventory
            adapted_curated = []
            for recipe in curated_recipes[:num_meals]:  # Limit to avoid processing too many
                adapted = adapt_recipe_to_inventory(recipe, inventory)
                adapted_curated.append({
                    **adapted,
                    "source": "curated",
                    "priority": 1  # High priority for curated recipes
                })

            all_sources.extend(adapted_curated)
            print(f"Adapted {len(adapted_curated)} curated recipes")

        # Step 2: If we don't have enough curated recipes, supplement with AI
        if len(all_sources) < num_meals // 2:
            ai_num = min(3, max(1, (num_meals - len(all_sources)) // 2))
            print(f"Generating {ai_num} AI recipes to supplement")

            ai_result = generate_meal_plan(ai_num, criteria, inventory)
            if ai_result.get("success"):
                ai_recipes = ai_result.get("meals", [])
                for meal in ai_recipes:
                    recipe = meal.get("recipe", {})
                    recipe["source"] = "ai"
                    recipe["priority"] = 2  # Medium priority
                    all_sources.append({"recipe": recipe})
                print(f"Generated {len(ai_recipes)} AI recipes")

        # Step 3: If still need more, fetch API recipes
        if len(all_sources) < num_meals:
            api_num = min(10, max(5, num_meals))
            print(f"Fetching {api_num} API recipes to supplement")

            api_result = get_suggested_recipes(inventory, api_num)
            if api_result.get("success"):
                api_recipes = api_result.get("recipes", [])
                for recipe in api_recipes[:num_meals - len(all_sources)]:
                    recipe["source"] = "api_ninjas"
                    recipe["priority"] = 3  # Lower priority
                    all_sources.append({"recipe": recipe})
                print(f"Fetched {len(api_recipes)} API recipes")

        # Step 4: Curate all sources together
        if all_sources:
            from backend.recipe_curator import curate_recipes_with_ai

            # Extract recipes for curation
            recipes_to_curate = []
            for source in all_sources:
                if "recipe" in source:
                    recipes_to_curate.append(source["recipe"])
                else:
                    recipes_to_curate.append(source)

            # Split into AI and API for curator (it expects two lists)
            ai_recipes = [r for r in recipes_to_curate if r.get("source") == "ai"]
            other_recipes = [r for r in recipes_to_curate if r.get("source") != "ai"]

            curated_result = curate_recipes_with_ai(ai_recipes, other_recipes, num_meals, preferences)
            print(f"Curated down to {len(curated_result)} final recipes")

            # Convert to meal plan format
            meals = []
            for recipe in curated_result:
                if "recipe" in recipe:  # Already wrapped
                    meals.append(recipe)
                else:
                    meals.append({
                        "recipe": {
                            "name": recipe.get("name", "Unknown Recipe"),
                            "ingredients": recipe.get("ingredients", recipe.get("main_ingredients", [])),
                            "instructions": recipe.get("instructions", ""),
                            "source": recipe.get("source", "Unknown"),
                            "adaptation": recipe.get("adaptation")  # Include adaptation info if present
                        }
                    })

            return {
                "success": True,
                "count": len(meals),
                "meals": meals,
                "message": f"Generated {len(meals)} meals prioritizing your curated recipes"
            }
        else:
            # Fallback to standard unified meal planning
            return generate_unified_meal_plan(num_meals, criteria, inventory)

    except Exception as e:
        print(f"Error in curated meal planning: {e}")
        # Fallback to standard unified meal planning
        print("Falling back to standard unified meal planning...")
        return generate_unified_meal_plan(num_meals, criteria, inventory)
