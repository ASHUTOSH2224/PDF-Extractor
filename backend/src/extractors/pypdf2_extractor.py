from typing import Dict, Any, Union
from PyPDF2 import PdfReader
from src.interface import PDFExtractorInterface
from loguru import logger




class PyPDF2Extractor(PDFExtractorInterface):
    def __init__(self):
        self._last_result = None

    def get_information(self) -> dict:
        return {
            "name": "PyPDF2",
            "type": "sync",
            "supports": ["text"],
            "description": "Extracts text content from PDFs using PyPDF2."
        }

    def read(self, file_path: str, **kwargs) -> Dict[int, Dict[str, Any]]:
        """
        Extracts raw text from PDF pages using PyPDF2 synchronously.
        """
        page_contents: Dict[int, Dict[str, Any]] = {}
        try:
            reader = PdfReader(file_path)
            num_pages = len(reader.pages)
            for page_num in range(num_pages):
                page = reader.pages[page_num]
                text = page.extract_text() or ""
                page_contents[page_num + 1] = {
                    "content": {
                        "TEXT": text
                    },
                    "metadata": {
                        "extractor": "PyPDF2",
                        "page_number": page_num + 1
                    }
                }
        except Exception as e:
            logger.warning(f"PyPDF2 extraction failed: {str(e)}")
            page_contents = {
                1: {
                    "content": {"TEXT": ""},
                    "metadata": {"error": str(e)}
                }
            }
        self._last_result = page_contents
        return True

    def get_status(self, job_id: str) -> str:
        """
        PyPDF2 is synchronous; always returns 'succeeded'.
        """
        return "succeeded"

    def get_result(self, job_id: str) -> Union[str, dict]:
        """
        job_id is irrelevant for synchronous extractors; returns last result.
        """
        return self._last_result

    def supports_webhook(self) -> bool:
        """
        PyPDF2 does not support webhooks.
        """
        return False

    def handle_webhook(self, payload: dict) -> Union[str, dict]:
        """
        Webhook handling not supported for PyPDF2.
        """
        raise NotImplementedError("PyPDF2 does not support webhooks")
