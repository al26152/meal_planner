import pdfplumber
from backend.openai_client import extract_receipt_items
from config import UPLOAD_FOLDER
import os


# Non-food item keywords to filter out
NON_FOOD_KEYWORDS = {
    # Household and cleaning
    'toilet', 'tissue', 'paper towel', 'wipe', 'bleach', 'cleaner', 'detergent',
    'soap', 'shampoo', 'conditioner', 'deodorant', 'toothpaste', 'toothbrush',
    'sponge', 'dish brush', 'mop', 'broom', 'trash bag', 'garbage bag',
    'trash', 'garbage', 'plastic bag', 'bin bag', 'refuse',

    # Personal care
    'lotion', 'cream', 'moisturizer', 'sunscreen', 'razors', 'razor',
    'shave', 'lipstick', 'nail polish', 'makeup', 'perfume', 'cologne',
    'deodorant', 'antiperspirant', 'sanitary', 'pad', 'tampon', 'tissue',

    # Pets/non-food
    'pet food', 'dog food', 'cat food', 'pet shampoo', 'pet supplies',

    # Household items
    'light bulb', 'battery', 'candle', 'matches', 'lighter', 'tape',
    'glue', 'scissors', 'pen', 'pencil', 'notebook', 'paper', 'ink',
    'foil', 'wrap', 'saran', 'plastic wrap', 'aluminum foil',

    # Non-consumable items
    'magazine', 'newspaper', 'book', 'greeting card', 'card', 'stamp',
    'postage', 'phone card', 'lottery', 'ticket', 'fuel', 'gas',
    'clothing', 'shirt', 'pants', 'shoes', 'sock', 'underwear',
    'towel', 'sheet', 'pillow', 'blanket', 'mattress', 'furniture'
}


def is_food_item(item: dict) -> bool:
    """
    Check if an item is food-related.

    Args:
        item: Dictionary with item details

    Returns:
        True if item is food-related, False otherwise
    """
    name = item.get('name', '').lower()
    category = item.get('category', '').lower()

    # Check if name contains non-food keywords
    for keyword in NON_FOOD_KEYWORDS:
        if keyword in name:
            return False

    # Check for non-food categories (if OpenAI assigned one)
    non_food_categories = ['non-food', 'household', 'personal care', 'pet', 'other non-food']
    if category in non_food_categories:
        return False

    return True


def filter_non_food_items(items: list) -> list:
    """
    Filter out non-food items from the extracted list.

    Args:
        items: List of extracted items

    Returns:
        List of food items only
    """
    food_items = [item for item in items if is_food_item(item)]

    # Log filtered items
    if len(food_items) < len(items):
        filtered_count = len(items) - len(food_items)
        print(f"Filtered out {filtered_count} non-food items")

    return food_items


def process_receipt_file(file_path: str) -> list:
    """
    Process an uploaded receipt PDF and extract items.

    Args:
        file_path: Path to the uploaded .pdf file

    Returns:
        List of extracted inventory items from receipt
    """

    try:
        # Extract text from PDF
        receipt_text = extract_text_from_pdf(file_path)

        if not receipt_text:
            print(f"Warning: No text extracted from PDF at {file_path}")
            return []

        print(f"Extracted receipt text ({len(receipt_text)} chars): {receipt_text[:200]}...")

        # Extract items using OpenAI
        items = extract_receipt_items(receipt_text)

        print(f"Extracted {len(items)} items from receipt")

        # Filter out non-food items
        food_items = filter_non_food_items(items)

        print(f"After filtering: {len(food_items)} food items remaining")
        return food_items

    except Exception as e:
        print(f"Error processing receipt file: {e}")
        return []


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text content from a PDF file, including tables.

    Args:
        file_path: Path to the PDF file

    Returns:
        Extracted text from PDF
    """

    try:
        text = ""

        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                # Extract regular text from page
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

                # Also try to extract tables (common in receipts)
                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        for row in table:
                            # Join row items with space
                            row_text = " | ".join(str(cell) if cell else "" for cell in row)
                            text += row_text + "\n"

        return text.strip()

    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""


def save_uploaded_file(file, filename: str) -> str:
    """
    Save uploaded file to the receipts folder.

    Args:
        file: Flask file object
        filename: Original filename

    Returns:
        Path to saved file
    """

    try:
        receipt_folder = os.path.join(UPLOAD_FOLDER, 'receipts')
        os.makedirs(receipt_folder, exist_ok=True)
        file_path = os.path.join(receipt_folder, filename)
        file.save(file_path)
        return file_path
    except Exception as e:
        print(f"Error saving receipt file: {e}")
        return None
