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

    prompt = f"""Extract all food/grocery items from this receipt. For each item, provide:
- name: the product/food item name (string)
- quantity: the amount purchased (number, default 1 if not specified)
- unit: measurement unit (string: grams, kg, ml, l, pieces, items, pack, bottle, etc.)
- category: food category (string: dairy, produce, meat, pantry, frozen, beverages, bakery, other)

Return ONLY a valid JSON array with these fields. Do not include any other text.
If quantity is unclear, use the pack size or estimate reasonably.

Receipt text:
{receipt_text}

Return JSON array:"""

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
            max_tokens=1500
        )

        response_text = response.choices[0].message.content.strip()

        # Handle markdown code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

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
        print(f"Error parsing OpenAI response: {e}")
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
            max_tokens=1000
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
