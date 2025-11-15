import json
from openai import OpenAI
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

def extract_receipt_items(receipt_text: str) -> list:
    """
    Extract food items from receipt text using OpenAI GPT-4o-mini.

    Args:
        receipt_text: Text extracted from PDF receipt

    Returns:
        List of inventory items with name, quantity, unit, and category
    """

    prompt = f"""You are a receipt parser. Extract EVERY food, grocery, and beverage item from this receipt.

For each item, provide:
- name: the product/food item name (string, use simple text without special quotes)
- quantity: the amount purchased (number, default 1 if not specified)
- unit: measurement unit (string: grams, kg, ml, l, pieces, items, pack, bottle, can, box, etc.)
- category: food category (string: dairy, produce, meat, pantry, frozen, beverages, bakery, other)

CRITICAL RULES:
- Include ALL food and grocery items (even small items)
- Do not include non-food items (plastic bags, household items, toiletries, etc.)
- Each item name must be a simple string without special characters or quotes inside
- Return a valid JSON array that can be parsed by Python
- NO markdown code blocks, NO explanations, ONLY valid JSON

Receipt text:
{receipt_text}

Return ONLY a valid JSON array like this format:
[{{"name": "item1", "quantity": 1, "unit": "pieces", "category": "produce"}}, {{"name": "item2", "quantity": 2, "unit": "grams", "category": "dairy"}}]"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a receipt parser. Extract food items accurately from receipt text and return only valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=10000,
            timeout=60.0
        )

        response_text = response.choices[0].message.content.strip()

        print(f"Raw OpenAI response: {response_text[:300]}...")

        # Handle markdown code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        print(f"Cleaned response: {response_text[:300]}...")

        items = json.loads(response_text)

        if not isinstance(items, list):
            items = [items] if isinstance(items, dict) else []

        # Validate items
        validated_items = []
        for item in items:
            if isinstance(item, dict) and "name" in item:
                validated_item = {
                    "name": str(item.get("name", "")).lower().strip(),
                    "quantity": float(item.get("quantity", 1)),
                    "unit": str(item.get("unit", "pieces")).lower().strip(),
                    "category": str(item.get("category", "other")).lower().strip()
                }
                if validated_item["name"]:
                    validated_items.append(validated_item)

        return validated_items

    except json.JSONDecodeError as e:
        print(f"Error parsing JSON (line {e.lineno}, col {e.colno}): {e.msg}")
        print(f"Attempting to fix malformed JSON...")

        # Try to fix common JSON issues
        try:
            # Try to find and fix unterminated strings
            fixed_response = response_text

            # Replace problematic unicode/special characters
            fixed_response = fixed_response.encode('utf-8', 'ignore').decode('utf-8')

            # Try parsing again
            items = json.loads(fixed_response)

            if not isinstance(items, list):
                items = [items] if isinstance(items, dict) else []

            print(f"Successfully recovered {len(items)} items after fixing JSON")
            return items

        except Exception as recovery_error:
            print(f"Could not recover JSON: {recovery_error}")
            print(f"Full response text:\n{response_text}")
            return []
    except Exception as e:
        print(f"Error extracting receipt items: {e}")
        return []



def extract_inventory_items(transcription_text: str) -> list:
    """
    Extract food items from transcription text using OpenAI GPT-4o-mini.

    Args:
        transcription_text: Plain text transcription from Google Recorder

    Returns:
        List of inventory items with name, quantity, unit, and category
    """

    prompt = f"""Extract all food items mentioned in this transcription. For each item, provide:
- name: the food item name (string)
- quantity: the amount (number, default 1 if not specified)
- unit: measurement unit (string: grams, ml, pieces, items, servings, etc. Use "pieces" if unknown)
- category: food category (string: dairy, produce, meat, pantry, frozen, beverages, other)

If an item doesn't have a clear quantity, estimate based on context or use 1.
Return ONLY a valid JSON array with these fields. Do not include any other text.

Transcription:
{transcription_text}

Return JSON array:"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a food inventory assistant. Extract food items from text accurately and return only valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,  # Low temperature for consistent extraction
            max_tokens=10000,
            timeout=60.0
        )

        # Extract the response text
        response_text = response.choices[0].message.content.strip()

        # Parse JSON from response
        # Handle cases where JSON might be wrapped in markdown code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        items = json.loads(response_text)

        # Validate items
        if not isinstance(items, list):
            items = [items] if isinstance(items, dict) else []

        # Ensure all items have required fields
        validated_items = []
        for item in items:
            if isinstance(item, dict) and "name" in item:
                validated_item = {
                    "name": str(item.get("name", "")).lower().strip(),
                    "quantity": float(item.get("quantity", 1)),
                    "unit": str(item.get("unit", "pieces")).lower().strip(),
                    "category": str(item.get("category", "other")).lower().strip()
                }
                # Only add if name is not empty
                if validated_item["name"]:
                    validated_items.append(validated_item)

        return validated_items

    except json.JSONDecodeError as e:
        print(f"Error parsing OpenAI response: {e}")
        return []
    except Exception as e:
        print(f"Error extracting inventory items: {e}")
        return []


def parse_manual_ingredient(user_input: str) -> list:
    """
    Parse manually entered ingredient text using OpenAI.
    Handles natural language input like "2 lbs chicken, 3 tomatoes, 1 gallon milk"

    Args:
        user_input: Free-text ingredient input from user

    Returns:
        List of parsed items with name, quantity, unit, and category
    """

    prompt = f"""Parse this ingredient entry into structured format. Extract each food item mentioned.

For each item, provide:
- name: the food item name (string, lowercase, no special characters)
- quantity: the amount (number, default 1 if not specified)
- unit: measurement unit (grams, kg, ml, l, pieces, lbs, oz, cup, tbsp, tsp, etc. Use "pieces" if not specified)
- category: food category (dairy, produce, meat, pantry, frozen, beverages, bakery, snacks, other)

RULES:
- Parse multiple items separated by commas
- Convert common abbreviations (lbs→lbs, oz→oz, etc.)
- If unit is ambiguous, guess the most likely (e.g., "2 chicken" → quantity: 2, unit: "pieces")
- Return ONLY valid JSON array, NO explanations

User input: {user_input}

Return JSON array:"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a food inventory assistant. Parse ingredient text accurately and return only valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2,  # Very low for consistent parsing
            max_tokens=1000,
            timeout=60.0
        )

        response_text = response.choices[0].message.content.strip()

        # Handle markdown code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        items = json.loads(response_text)

        # Validate items
        if not isinstance(items, list):
            items = [items] if isinstance(items, dict) else []

        # Ensure all items have required fields
        validated_items = []
        for item in items:
            if isinstance(item, dict) and "name" in item:
                validated_item = {
                    "name": str(item.get("name", "")).lower().strip(),
                    "quantity": float(item.get("quantity", 1)),
                    "unit": str(item.get("unit", "pieces")).lower().strip(),
                    "category": str(item.get("category", "other")).lower().strip()
                }
                # Only add if name is not empty
                if validated_item["name"]:
                    validated_items.append(validated_item)

        return validated_items

    except json.JSONDecodeError as e:
        print(f"Error parsing manual ingredient JSON: {e}")
        return []
    except Exception as e:
        print(f"Error parsing manual ingredient: {e}")
        return []


def adapt_recipe_to_inventory(recipe: dict, inventory_items: list) -> dict:
    """
    Adapt a curated recipe to use available inventory items.
    Uses AI to suggest substitutions and modifications.

    Args:
        recipe: Recipe dict with name, ingredients, instructions
        inventory_items: List of available inventory items with names and quantities

    Returns:
        Adapted recipe dict with modifications and notes
    """

    try:
        # Validate inputs
        if not recipe:
            print("Error: recipe is None or empty")
            return {'adaptation': {'can_make': False, 'error': 'Recipe is empty'}}

        if not isinstance(recipe, dict):
            print(f"Error: recipe is not a dict, it's {type(recipe)}")
            return {'adaptation': {'can_make': False, 'error': 'Invalid recipe format'}}

        if not inventory_items:
            inventory_items = []

        if not isinstance(inventory_items, list):
            print(f"Error: inventory_items is not a list, it's {type(inventory_items)}")
            inventory_items = []

        # If recipe has no ingredients, return as-is
        recipe_ingredients = recipe.get('ingredients', [])
        if not recipe_ingredients or len(recipe_ingredients) == 0:
            return recipe

        # Prepare inventory info for the prompt
        inventory_names = [item.get('name', '').lower() for item in inventory_items if item and item.get('quantity', 0) > 0]

        # If no inventory, return early with basic adaptation info
        if not inventory_names:
            print("No inventory items available, skipping AI adaptation")
            return {
                **recipe,
                'adaptation': {
                    'can_make': False,
                    'match_percentage': 0,
                    'notes': 'Add items to your inventory to get adaptation suggestions'
                }
            }

        # Validate and clean recipe ingredients
        cleaned_ingredients = []
        for ing in recipe_ingredients:
            if not ing:
                continue
            if not isinstance(ing, dict):
                print(f"Warning: ingredient is not a dict: {ing}")
                continue

            ing_name = ing.get('name')
            if not ing_name:
                continue

            qty = ing.get('quantity', 1)
            if qty is None:
                qty = 1

            cleaned_ingredients.append({
                'name': str(ing_name).lower().strip(),
                'quantity': float(qty) if isinstance(qty, (int, float)) else 1,
                'unit': str(ing.get('unit', '')).lower().strip() or ''
            })

        # Build ingredient list with what user has vs what's missing
        have = []
        need = []

        for ingredient in cleaned_ingredients:
            ing_name = ingredient.get('name', '').lower()
            # Simple check - could be enhanced with fuzzy matching
            if any(ing_name in inv or inv in ing_name for inv in inventory_names):
                have.append(ing_name)
            else:
                need.append(ing_name)

        prompt = f"""You are a culinary expert. Adapt this recipe to work with available ingredients.

RECIPE: {recipe.get('name', 'Unknown Recipe')}

INGREDIENTS IN RECIPE:
{json.dumps(cleaned_ingredients, indent=2)}

INGREDIENTS AVAILABLE:
{json.dumps(inventory_items, indent=2)}

USER HAS: {', '.join(have) if have else 'very few of the main ingredients'}
USER NEEDS: {', '.join(need) if need else 'all ingredients'}

INSTRUCTIONS: {recipe.get('instructions', '')[:500]}

Return ONLY a JSON object with this structure:
{{
    "can_make": true or false,
    "match_percentage": 75,
    "missing_ingredients": ["ingredient1", "ingredient2"],
    "substitutions": [
        {{"original": "butter", "substitute": "oil", "reason": "better for hot cooking"}}
    ],
    "adaptations": [
        "Use olive oil instead of butter",
        "Cooking time may increase by 5 minutes"
    ],
    "adapted_instructions": "Modified step-by-step instructions if needed, or null if no changes needed",
    "notes": "General notes about how well this recipe works with available ingredients"
}}

RULES:
- can_make: true if user has 60%+ of ingredients or good substitutions exist
- match_percentage: 0-100 of how well recipe matches available ingredients
- Suggest practical substitutions only (e.g., oil for butter, but not beef for chicken)
- If instructions need to change due to substitutions, update them
- Return ONLY valid JSON"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a culinary expert. Analyze recipes and suggest practical adaptations for available ingredients."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.5,
            max_tokens=1500,
            timeout=60.0
        )

        # Validate response structure
        if not response or not response.choices or len(response.choices) == 0:
            print(f"Invalid response structure: {response}")
            raise ValueError("Empty response from OpenAI")

        message = response.choices[0].message
        if not message or not message.content:
            print(f"Invalid message structure: {message}")
            raise ValueError("No content in message")

        response_text = message.content.strip()

        # Handle markdown code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        adaptation_data = json.loads(response_text)

        # Return adapted recipe with original data + adaptation info
        adapted_recipe = recipe.copy()
        adapted_recipe['adaptation'] = adaptation_data
        adapted_recipe['adapted'] = True

        return adapted_recipe

    except json.JSONDecodeError as e:
        print(f"Error parsing adaptation response: {e}")
        import traceback
        traceback.print_exc()
        # Return original recipe if adaptation fails
        return {
            **recipe,
            'adaptation': {
                'can_make': True,
                'match_percentage': 0,
                'error': 'Could not analyze recipe adaptation'
            }
        }
    except Exception as e:
        print(f"Error adapting recipe: {e}")
        import traceback
        traceback.print_exc()
        # Return original recipe if adaptation fails
        return {
            **recipe,
            'adaptation': {
                'can_make': True,
                'match_percentage': 0,
                'error': str(e)
            }
        }
