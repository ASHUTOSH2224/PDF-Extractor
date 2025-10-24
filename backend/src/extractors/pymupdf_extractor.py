import fitz  # PyMuPDF
from typing import Dict, Any, Union
from src.interface import PDFExtractorInterface

class PyMuPDFExtractor(PDFExtractorInterface):
    def __init__(self):
        self._last_result = None

    def get_information(self) -> dict:
        return {
            "name": "PyMuPDF",
            "type": "sync",
            "supports": ["text"],   # PyMuPDF is mainly for text, not structured tables
            "description": "Extracts raw text (and metadata if needed) using PyMuPDF (fitz)."
        }

    def read(self, file_path: str, **kwargs) -> Dict[int, Dict[str, str]]:
        """
        Extract text from PDF using PyMuPDF synchronously.
        """
        page_contents: Dict[int, Dict[str, str]] = {}

        doc = fitz.open(file_path)

        for page_num in range(doc.page_count):
            page = doc[page_num]
            text = page.get_text()

            page_contents[page_num + 1] = {
                "content": {
                    "TEXT": text or ""
                }
            }

        doc.close()
        self._last_result = page_contents
        return True

    def get_status(self, job_id: str) -> str:
        # Always succeeds immediately since PyMuPDF is sync
        return "succeeded"

    def get_result(self, job_id: str) -> Union[str, dict]:
        # job_id is irrelevant for sync; return last result
        return self._last_result

    def supports_webhook(self) -> bool:
        return False

    def handle_webhook(self, payload: dict) -> Union[str, dict]:
        raise NotImplementedError("PyMuPDF does not support webhooks")
