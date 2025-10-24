import pdfplumber
from typing import Dict, Any, Union
from src.interface import PDFExtractorInterface

class PDFPlumberExtractor(PDFExtractorInterface):
    def __init__(self):
        self._last_result = None

    def get_information(self) -> dict:
        return {
            "name": "pdfplumber",
            "type": "sync",
            "supports": ["combined", "tables"],
            "description": "Extracts text and tables from PDFs using PDFPlumber."
        }

    def read(self, file_path: str, **kwargs) -> Dict[int, Dict[str, Dict[str, str]]]:
        """
        Extract text and tables from PDF synchronously.
        Stores result internally and returns it directly.
        """
        page_contents = {}

        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                # Extract text (includes table content as text too)
                text = page.extract_text()

                # Extract tables separately
                tables = page.extract_tables()

                # Format tables into string representation
                table_strings = []
                if tables:
                    for table in tables:
                        if table:
                            table_str = ""
                            for row in table:
                                if row:
                                    table_str += " | ".join(str(cell) if cell else "" for cell in row) + "\n"
                            table_strings.append(table_str.strip())

                # Structured content
                content = {
                    "COMBINED": text or "",
                    "TABLE": "\n\n".join(table_strings) if table_strings else ""
                }

                page_contents[page_num] = {"content": content}

        self._last_result = page_contents
        return page_contents

    def get_status(self, job_id: str) -> str:
        # Always succeeds immediately since pdfplumber is sync
        return "succeeded"

    def get_result(self, job_id: str) -> Union[str, dict]:
        # job_id is irrelevant for sync; just return last result
        return self._last_result

    def supports_webhook(self) -> bool:
        # Local libraries don’t support webhooks
        return False

    def handle_webhook(self, payload: dict) -> Union[str, dict]:
        raise NotImplementedError("PDFPlumber does not support webhooks")