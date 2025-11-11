import json
from openai import OpenAI
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)


def curate_recipes_with_ai(ai_recipes: list, api_recipes: list, num_meals: int, preferences: dict) -> list:
    """
    Use AI to curate and combine recipes from both AI and API sources.

    Removes duplicates, ensures variety, balances nutrition, and ensures practicality.

    Args:
        ai_recipes: List of AI-generated recipes (from generate_meal_plan)
        api_recipes: List of API recipes (from search_recipes_by_type or get_suggested_recipes)
        num_meals: Number of final meals to return
        preferences: User preferences dict

    Returns:
        List of curated recipes (combined and balanced)
    """

    if not ai_recipes and not api_recipes:
        return []

    # Format recipes for the prompt
    ai_recipes_text = _format_recipes_for_curation(ai_recipes, "AI-Generated")
    api_recipes_text = _format_recipes_for_curation(api_recipes, "API Recipe Database")

    # Get dietary preferences for the prompt
    dietary_restrictions = preferences.get("dietary_restrictions", [])
    cuisine_types = preferences.get("cuisine_types", [])
    exclude_ingredients = preferences.get("ingredient_preferences", {}).get("exclude", [])
    nutritional_goals = preferences.get("nutritional_goals", [])

    prompt = f"""You are a professional meal planner. I have two sets of recipes and need you to curate them into a balanced meal plan.

USER PREFERENCES:
- Dietary Restrictions: {', '.join(dietary_restrictions) if dietary_restrictions else 'None'}
- Preferred Cuisines: {', '.join(cuisine_types) if cuisine_types else 'None'}
- Ingredients to Avoid: {', '.join(exclude_ingredients) if exclude_ingredients else 'None'}
- Nutritional Goals: {', '.join(nutritional_goals) if nutritional_goals else 'Balanced'}

AI-GENERATED RECIPES (Custom recipes):
{ai_recipes_text}

API RECIPES (Real recipes from database):
{api_recipes_text}

TASK: Combine and curate these recipes into {num_meals} best meals by:
1. Removing duplicates or very similar recipes (e.g., if both have pasta dishes, keep only the best one)
2. Ensuring variety: different cuisines, cooking methods, ingredient profiles
3. Balancing nutrition: mix of protein-rich, vegetable-heavy, and carb-based dishes
4. Ensuring practicality: avoid recipes with too many hard-to-find ingredients (unless already in preferences)
5. Prioritizing quality: mix AI creativity with API's real-world tested recipes
6. Respecting preferences: ensure no excluded ingredients are used

For each final recipe, include:
- Name
- Source (AI or API)
- Cuisine/Type
- Main ingredients (as a list)
- Estimated cooking time
- Why it was selected (2 sentences max)

Return as a JSON array with {num_meals} recipes. Each recipe should have:
{{"name": "...", "source": "AI" or "API", "cuisine": "...", "main_ingredients": [...], "cooking_time": "...", "reason": "..."}}

Be concise. Return ONLY valid JSON, no markdown or explanation."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert meal planner. Curate and balance recipes from multiple sources to create a diverse, nutritious meal plan. Return only valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,  # Moderate creativity for curation
            max_tokens=2000,
            timeout=60.0  # 60 second timeout for API call
        )

        response_text = response.choices[0].message.content.strip()

        # Handle markdown code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        curated = json.loads(response_text)

        # Validate response is a list
        if not isinstance(curated, list):
            curated = [curated] if isinstance(curated, dict) else []

        return curated[:num_meals]  # Ensure we return exactly num_meals

    except json.JSONDecodeError as e:
        print(f"Error parsing curation response: {e}")
        # Fallback: combine recipes simply if AI curation fails
        return _simple_combine_recipes(ai_recipes, api_recipes, num_meals)
    except Exception as e:
        print(f"Error during recipe curation: {e}")
        # Fallback to simple combination
        return _simple_combine_recipes(ai_recipes, api_recipes, num_meals)


def _format_recipes_for_curation(recipes: list, source_label: str) -> str:
    """Format recipes nicely for the curation prompt."""
    if not recipes:
        return f"No {source_label} recipes available"

    lines = []
    for i, recipe in enumerate(recipes, 1):
        # Handle different recipe formats
        if "recipe" in recipe:  # AI-generated format
            recipe_data = recipe["recipe"]
            name = recipe_data.get("name", "Unknown")
            ingredients = recipe_data.get("ingredients", [])
            instructions = recipe_data.get("instructions", "")[:100] + "..."  # First 100 chars
        else:  # API format
            name = recipe.get("name", "Unknown")
            ingredients = recipe.get("ingredients", []) or recipe.get("main_ingredients", [])
            instructions = recipe.get("instructions", "")[:100] + "..."

        # Format ingredients list
        if isinstance(ingredients, list):
            if ingredients and isinstance(ingredients[0], dict):
                ingredient_names = [ing.get("name", "") for ing in ingredients]
            else:
                ingredient_names = [str(ing) for ing in ingredients]
        else:
            ingredient_names = []

        ingredient_str = ", ".join(ingredient_names[:5])  # First 5 ingredients
        if len(ingredient_names) > 5:
            ingredient_str += f", +{len(ingredient_names)-5} more"

        line = f"{i}. {name} | Ingredients: {ingredient_str} | Preview: {instructions}"
        lines.append(line)

    return "\n".join(lines)


def _simple_combine_recipes(ai_recipes: list, api_recipes: list, num_meals: int) -> list:
    """
    Fallback: Simple combination of AI and API recipes without AI curation.
    Alternates between sources and limits to num_meals.
    """
    combined = []

    # Alternate between AI and API recipes
    for i in range(num_meals):
        if i % 2 == 0:
            # Try to get from AI recipes
            if ai_recipes and len(ai_recipes) > i // 2:
                recipe = ai_recipes[i // 2]
                # Add source metadata
                if "recipe" in recipe:
                    recipe["source"] = "AI"
                combined.append(recipe)
            # Fallback to API
            elif api_recipes and len(api_recipes) > i // 2:
                recipe = api_recipes[i // 2]
                recipe["source"] = "API"
                combined.append(recipe)
        else:
            # Try to get from API recipes
            if api_recipes and len(api_recipes) > i // 2:
                recipe = api_recipes[i // 2]
                recipe["source"] = "API"
                combined.append(recipe)
            # Fallback to AI
            elif ai_recipes and len(ai_recipes) > i // 2:
                recipe = ai_recipes[i // 2]
                if "recipe" in recipe:
                    recipe["source"] = "AI"
                combined.append(recipe)

    return combined[:num_meals]
