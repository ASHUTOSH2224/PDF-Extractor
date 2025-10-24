from loguru import logger
from typing import Dict, Any, Union
import pytesseract
from PIL import Image
import fitz  # PyMuPDF
from io import BytesIO
from src.interface import PDFExtractorInterface


class TesseractExtractor(PDFExtractorInterface):
    def __init__(self):
        self._last_result = None

    def get_information(self) -> dict:
        return {
            "name": "Tesseract",
            "type": "sync",
            "supports": ["text"],
            "description": "Extracts text from scanned PDFs or image files using Tesseract OCR."
        }

    def read(self, file_path: str, **kwargs) -> Dict[int, Dict[str, Any]]:
        """
        Extracts text from each page of a scanned PDF or image file using Tesseract OCR.
        """
        page_contents: Dict[int, Dict[str, Any]] = {}
        try:
            # Convert each page to an image (if it's a PDF) using PyMuPDF (no Poppler needed)
            if file_path.lower().endswith(".pdf"):
                images = []
                with fitz.open(file_path) as doc:
                    for page in doc:
                        pix = page.get_pixmap(dpi=200)
                        img_bytes = pix.tobytes("png")
                        images.append(Image.open(BytesIO(img_bytes)))
            else:
                images = [Image.open(file_path)]
            for i, image in enumerate(images, start=1):
                text = pytesseract.image_to_string(image)
                page_contents[i] = {
                    "content": {
                        "TEXT": text.strip()
                    },
                    "metadata": {
                        "extractor": "Tesseract",
                        "page_number": i
                    }
                }
        except Exception as e:
            logger.error(f"Tesseract extraction failed: {str(e)}")
            raise e
        self._last_result = page_contents
        return page_contents

    def get_status(self, job_id: str) -> str:
        """
        Tesseract is synchronous; always returns 'succeeded'.
        """
        return "succeeded"

    def get_result(self, job_id: str) -> Union[str, dict]:
        """
        job_id is irrelevant for sync extractors; returns last result.
        """
        return self._last_result

    def supports_webhook(self) -> bool:
        """
        Tesseract does not support webhooks.
        """
        return False

    def handle_webhook(self, payload: dict) -> Union[str, dict]:
        """
        Webhook handling not supported for Tesseract.
        """
        raise NotImplementedError("Tesseract does not support webhooks")
