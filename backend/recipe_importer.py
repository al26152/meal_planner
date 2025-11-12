"""
Recipe Importer
Extracts recipe information from URLs using OpenAI
"""
import json
import requests
from typing import Dict, Optional, List
from openai import OpenAI
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)


def extract_text_from_url(url: str) -> Optional[str]:
    """
    Fetch and extract text content from a URL.

    Args:
        url: URL to fetch from

    Returns:
        Text content or None if fetch failed
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # Basic HTML to text extraction
        # For more robust extraction, would use BeautifulSoup
        text = response.text

        # Remove script and style tags
        import re
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)

        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)

        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        return text[:8000]  # Limit to 8000 chars for API processing

    except Exception as e:
        print(f"Error fetching URL {url}: {str(e)}")
        return None


def extract_recipe_from_text(content: str, source_url: Optional[str] = None) -> Optional[Dict]:
    """
    Extract structured recipe data from text using OpenAI.

    Args:
        content: Text content containing recipe information
        source_url: Original URL source (optional)

    Returns:
        Recipe dict with name, ingredients, instructions, or None if extraction failed
    """
    if not content:
        return None

    # Clean up content - remove links and cross-references
    import re
    cleaned_content = re.sub(r'https?://\S+', '', content)  # Remove URLs
    cleaned_content = re.sub(r'How To Make.*?-\s*•.*?\n', '', cleaned_content)  # Remove cross-references

    prompt = f"""Extract the recipe information from this messy recipe text. Be flexible with formatting.

Return ONLY valid JSON with this structure:
{{
    "name": "Recipe Name",
    "ingredients": [
        {{"name": "ingredient name", "quantity": 1.0, "unit": "cups"}}
    ],
    "instructions": "Cooking instructions if available, or null"
}}

RULES:
- Return ONLY valid JSON
- ingredients: Extract ALL items that look like ingredients with quantities/units
  - Parse quantities as numbers (e.g., "1/2" → 0.5, "1 & 1/4" → 1.25)
  - Keep units as strings (tsp, tbsp, gm, g, cups, etc)
  - Keep ingredient names simple and clean (e.g., "chickpeas" not "cooked chickpeas")
- instructions: If you find a "How to make" section, extract it. Otherwise null
- name: Recipe name if clear, or create from ingredients (e.g., "Chickpea Butter Masala")
- IMPORTANT: Do NOT return empty ingredients list - extract every ingredient you see
- If quantity/unit unclear, use quantity: 1, unit: "piece" or "tbsp"

Text:
{cleaned_content}

Return ONLY JSON, no explanations:"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a recipe extraction specialist. Extract recipe data from text and return ONLY valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=2000,
            timeout=60.0
        )

        response_text = response.choices[0].message.content.strip()

        # Handle markdown code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        recipe_data = json.loads(response_text)

        # Validate and clean the data
        if isinstance(recipe_data, dict):
            # Ensure recipe has a name
            if not recipe_data.get('name'):
                return None

            # Validate ingredients - MUST have at least one
            ingredients = recipe_data.get('ingredients', [])
            if isinstance(ingredients, list) and len(ingredients) > 0:
                validated_ingredients = []
                for ing in ingredients:
                    if isinstance(ing, dict) and 'name' in ing:
                        ing_name = str(ing.get('name', '')).lower().strip()
                        # Skip empty ingredient names
                        if ing_name:
                            validated_ingredients.append({
                                'name': ing_name,
                                'quantity': float(ing.get('quantity', 1)) if ing.get('quantity') else 1,
                                'unit': str(ing.get('unit', '')).lower().strip() or 'piece'
                            })

                if len(validated_ingredients) > 0:
                    recipe_data['ingredients'] = validated_ingredients
                else:
                    # No valid ingredients found
                    return None
            else:
                # No ingredients at all
                return None

            # Instructions can be null (user can add later)
            if 'instructions' not in recipe_data:
                recipe_data['instructions'] = ''

            # Add source if provided
            if source_url:
                recipe_data['source_url'] = source_url

            return recipe_data

        return None

    except json.JSONDecodeError as e:
        print(f"Error parsing recipe JSON: {str(e)}")
        return None
    except Exception as e:
        print(f"Error extracting recipe with AI: {str(e)}")
        return None


def import_recipe_from_url(url: str) -> Optional[Dict]:
    """
    Import a recipe from a URL.
    Fetches the URL content and extracts recipe data using AI.

    Args:
        url: Recipe URL to import

    Returns:
        Recipe dict or None if import failed
    """
    # Fetch content from URL
    content = extract_text_from_url(url)

    if not content:
        return None

    # Extract recipe using AI
    recipe = extract_recipe_from_text(content, source_url=url)

    if recipe:
        recipe['source'] = 'website'
        recipe['source_url'] = url

    return recipe


def import_recipe_from_youtube(url: str) -> Optional[Dict]:
    """
    Import a recipe from a YouTube video.

    NOTE: YouTube blocks web scrapers, so we can't extract recipe data reliably.
    Instead, we return a partial recipe and ask user to enter details manually.

    Args:
        url: YouTube video URL

    Returns:
        Partial recipe dict for manual completion
    """
    try:
        import re

        # Extract video ID
        video_id_match = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([^&\n?#]+)', url)
        if not video_id_match:
            return None

        video_id = video_id_match.group(1)

        # YouTube blocks scrapers, so just return empty recipe for manual entry
        # User will paste/enter recipe details in the form
        return {
            'name': f'YouTube Recipe',
            'ingredients': [],
            'instructions': '',
            'source': 'youtube',
            'source_url': url,
            'needs_manual_entry': True,
            'reason': 'YouTube videos cannot be automatically parsed. Please enter the recipe details below.'
        }

    except Exception as e:
        print(f"Error processing YouTube URL: {str(e)}")
        return {
            'name': 'Recipe from YouTube',
            'ingredients': [],
            'instructions': '',
            'source': 'youtube',
            'source_url': url,
            'needs_manual_entry': True,
            'reason': f'Please enter recipe details manually.'
        }


def import_recipe_manual(name: str, ingredients: List[Dict], instructions: str,
                        prep_time: Optional[str] = None,
                        cook_time: Optional[str] = None,
                        servings: Optional[str] = None,
                        cuisine: Optional[str] = None,
                        source_url: Optional[str] = None) -> Dict:
    """
    Create a recipe from manual input.

    Args:
        name: Recipe name
        ingredients: List of ingredient dicts with name, quantity, unit
        instructions: Cooking instructions
        prep_time: Preparation time
        cook_time: Cooking time
        servings: Number of servings
        cuisine: Cuisine type
        source_url: Source URL if applicable

    Returns:
        Recipe dict
    """
    return {
        'name': name,
        'ingredients': ingredients,
        'instructions': instructions,
        'prep_time': prep_time,
        'cook_time': cook_time,
        'servings': servings,
        'cuisine': cuisine,
        'source': 'manual',
        'source_url': source_url
    }
