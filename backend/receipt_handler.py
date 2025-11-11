import pdfplumber
from backend.openai_client import extract_receipt_items
from config import UPLOAD_FOLDER
import os


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
        return items

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
