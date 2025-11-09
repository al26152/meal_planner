import os
from backend.openai_client import extract_inventory_items
from config import UPLOAD_FOLDER


def process_transcription_file(file_path: str) -> list:
    """
    Process an uploaded transcription file and extract inventory items.

    Args:
        file_path: Path to the uploaded .txt file

    Returns:
        List of extracted inventory items
    """

    try:
        # Read the transcription file
        with open(file_path, 'r', encoding='utf-8') as f:
            transcription_text = f.read().strip()

        if not transcription_text:
            return []

        # Extract items using OpenAI
        items = extract_inventory_items(transcription_text)

        return items

    except UnicodeDecodeError:
        # Try with different encoding
        try:
            with open(file_path, 'r', encoding='latin-1') as f:
                transcription_text = f.read().strip()
            items = extract_inventory_items(transcription_text)
            return items
        except Exception as e:
            print(f"Error processing transcription file: {e}")
            return []
    except Exception as e:
        print(f"Error processing transcription file: {e}")
        return []


def save_uploaded_file(file, filename: str) -> str:
    """
    Save uploaded file to the transcriptions folder.

    Args:
        file: Flask file object
        filename: Original filename

    Returns:
        Path to saved file
    """

    try:
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        return file_path
    except Exception as e:
        print(f"Error saving uploaded file: {e}")
        return None
