from markitdown import MarkItDown
from typing import Dict, Any, Union
from src.interface import PDFExtractorInterface
from loguru import logger


class MarkItDownExtractor(PDFExtractorInterface):
    def __init__(self):
        self._last_result = None

    def get_information(self) -> dict:
        return {
            "name": "MarkItDown",
            "type": "sync",
            "supports": ["text", "tables", "markdown"],
            "description": "Extracts text and converts to markdown format using MarkItDown."
        }

    def read(self, file_path: str, **kwargs):
        """
        Extract text from PDF and convert to markdown using MarkItDown synchronously.
        Returns a per-page mapping with extracted markdown content.
        """
        page_contents: Dict[int, Dict[str, Any]] = {}
        try:
            # Create MarkItDown instance and process the document
            md = MarkItDown()
            result = md.convert(file_path)
            
            # Extract text content and ensure it's not empty
            text_content = result.text_content if result.text_content else ""
            
            # Add debug logging to help troubleshoot content extraction
            logger.info(f"MarkItDown extracted content length: {len(text_content)}")
            if text_content:
                logger.debug(f"MarkItDown extracted content preview: {text_content[:200]}...")
            
            # MarkItDown returns the full document content as markdown
            # We'll treat it as a single page for now, but could be split by pages if needed
            page_contents[1] = {
                "content": {
                    "MARKDOWN": text_content,
                    "TEXT": text_content,  # Also provide as plain text
                    "COMBINED": text_content  # Add COMBINED key for meaningful content validation
                },
                "metadata": {
                    "extractor": "MarkItDown",
                    "format": "markdown",
                    "total_pages": 1
                }
            }
        except Exception as e:
            logger.warning(f"MarkItDown extraction failed: {str(e)}")
            page_contents = {
                1: {
                    "content": {
                        "MARKDOWN": "",
                        "TEXT": "",
                        "COMBINED": ""
                    },
                    "metadata": {"error": str(e)}
                }
            }
        self._last_result = page_contents
        return page_contents

    def get_status(self, job_id: str) -> str:
        """
        MarkItDown is synchronous; extraction always completes immediately.
        """
        return "succeeded"

    def get_result(self, job_id: str) -> Union[str, dict]:
        """
        job_id is unused for sync extractors; returns last result.
        """
        return self._last_result

    def supports_webhook(self) -> bool:
        """
        MarkItDown does not support webhooks.
        """
        return False

    def handle_webhook(self, payload: dict) -> Union[str, dict]:
        """
        Webhook handling not supported for MarkItDown.
        """
        raise NotImplementedError("MarkItDown does not support webhooks")
