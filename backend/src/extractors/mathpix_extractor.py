from loguru import logger
import requests
from typing import Dict, Any, Union
from src.interface import PDFExtractorInterface
from src.constants import MATHPIX_APP_ID, MATHPIX_APP_KEY

class MathpixExtractor(PDFExtractorInterface):
    def __init__(self):
        """
        Initialize Mathpix extractor with API credentials.
        """
        self.app_id = MATHPIX_APP_ID
        self.app_key = MATHPIX_APP_KEY
        self._last_result = None
        self.endpoint = "https://api.mathpix.com/v3/pdf"

    def get_information(self) -> dict:
        return {
            "name": "Mathpix",
            "type": "async",
            "supports": ["text", "latex", "markdown"],
            "description": "Extracts text and math expressions using Mathpix PDF API."
        }

    def read(self, file_path: str, **kwargs) -> str:
        """
        Upload PDF to Mathpix and return job ID for async processing.
        """
        headers = {
            "app_id": self.app_id,
            "app_key": self.app_key
        }

        try:
            with open(file_path, 'rb') as f:
                files = {'file': f}
                
                response = requests.post(
                    self.endpoint,
                    headers=headers,
                    files=files
                )
            
            response.raise_for_status()
            result = response.json()
            pdf_id = result.get('pdf_id')
            
            logger.info(f"PDF uploaded successfully. PDF ID: {pdf_id}")
            return pdf_id

        except Exception as e:
            logger.error(f"Mathpix PDF upload failed: {str(e)}")
            raise

    def get_status(self, job_id: str) -> str:
        """
        Check the processing status of the PDF.
        Returns: 'processing', 'completed', 'error'
        """
        headers = {
            "app_id": self.app_id,
            "app_key": self.app_key
        }

        try:
            response = requests.get(
                f"{self.endpoint}/{job_id}",
                headers=headers
            )
            response.raise_for_status()
            
            status_data = response.json()
            status = status_data.get('status', 'unknown')
            
            # Map Mathpix status to our standard statuses
            if status == 'completed':
                return 'succeeded'
            elif status == 'error':
                return 'failed'
            else:
                return 'processing'

        except Exception as e:
            logger.error(f"Failed to check status: {str(e)}")
            return 'failed'

    def get_result(self, job_id: str, output_format: str = 'mmd') -> Union[str, dict]:
        """
        Get the processed results from Mathpix using lines.json format.
        
        Args:
            job_id: The PDF ID returned from read()
            output_format: Ignored - we use lines.json format
        
        Returns:
            Dict with page contents in the standard format
        """
        headers = {
            "app_id": self.app_id,
            "app_key": self.app_key
        }

        try:
            # Get the structured lines data from Mathpix
            lines_response = requests.get(
                f"{self.endpoint}/{job_id}.lines.json",
                headers=headers
            )
            lines_response.raise_for_status()
            lines_data = lines_response.json()
            
            # Parse the structured response
            page_contents: Dict[int, Dict[str, Any]] = {}
            
            if 'pages' in lines_data and isinstance(lines_data['pages'], list):
                for page_data in lines_data['pages']:
                    page_num = page_data.get('page', 1)
                    lines = page_data.get('lines', [])
                    
                    # Sort lines by line number
                    sorted_lines = sorted(lines, key=lambda x: x.get('line', 0))
                    
                    # Collect text from text_display field, filtering out empty ones
                    page_text_lines = []
                    for line in sorted_lines:
                        text_display = line.get('text_display', '').strip()
                        if text_display:  # Only include non-empty text
                            page_text_lines.append(text_display)
                    
                    # Join all text lines for this page
                    page_text = '\n'.join(page_text_lines)
                    
                    page_contents[page_num] = {
                        "content": {
                            "LATEX": page_text  # Using the same text for both TEXT and LATEX
                        },
                        "metadata": {
                            "extractor": "Mathpix",
                            "pdf_id": job_id,
                            "page": page_num,
                            "total_lines": len(sorted_lines),
                            "format": "lines.json"
                        }
                    }
                    
                    logger.info(f"Processed page {page_num} with {len(page_text_lines)} text lines")
            else:
                # Fallback if pages structure is not as expected
                logger.warning("Unexpected response structure from Mathpix lines.json")
                page_contents[1] = {
                    "content": {
                        "LATEX": ""
                    },
                    "metadata": {
                        "extractor": "Mathpix",
                        "pdf_id": job_id,
                        "page": 1,
                        "error": "Unexpected response structure"
                    }
                }
            
            self._last_result = page_contents
            return page_contents

        except Exception as e:
            logger.error(f"Failed to get results: {str(e)}")
            return {
                1: {
                    "content": {
                        "LATEX": ""
                    },
                    "metadata": {"error": str(e)}
                }
            }

    def supports_webhook(self) -> bool:
        return False

    def handle_webhook(self, payload: dict) -> Union[str, dict]:
        raise NotImplementedError("Mathpix does not support webhooks")