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
            max_tokens=10000
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


def suggest_recipe_types(inventory: list) -> list:
    """
    Analyze inventory and suggest recipe types/cuisines to search for.

    Args:
        inventory: List of inventory items with names

    Returns:
        List of suggested recipe types/search terms
    """

    if not inventory:
        return []

    # Extract just the ingredient names
    ingredients = [item.get("name", "").strip() for item in inventory if item.get("name")]

    prompt = f"""Analyze these ingredients and suggest 3-5 specific recipe types or cuisines that would work well with them.

Ingredients available:
{', '.join(ingredients)}

For each suggestion, provide:
1. A specific recipe type or cuisine (e.g., "Italian Pasta", "Thai Curry", "Stir Fry", "Soup")
2. Brief reason why it matches the ingredients

Format as a simple list, one suggestion per line.
Be specific and practical - think of actual dish types that use these ingredients."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a culinary expert. Analyze available ingredients and suggest specific recipe types or cuisines that would work well."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=500
        )

        response_text = response.choices[0].message.content.strip()

        # Parse response into list of suggestions
        lines = response_text.split('\n')
        suggestions = []

        for line in lines:
            line = line.strip()
            if line and len(line) > 5:  # Filter out empty lines and very short lines
                # Extract just the recipe type (before any explanation)
                parts = line.split(' - ')
                if parts:
                    recipe_type = parts[0].strip()
                    # Remove common prefixes like numbers, bullets, etc.
                    recipe_type = recipe_type.lstrip('0123456789.)• ')
                    if recipe_type and len(recipe_type) > 3:
                        suggestions.append(recipe_type)

        return suggestions[:5]  # Return top 5 suggestions

    except Exception as e:
        print(f"Error suggesting recipe types: {e}")
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
            max_tokens=10000
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
