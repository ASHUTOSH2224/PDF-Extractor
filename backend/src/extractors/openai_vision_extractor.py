import openai
import fitz  # PyMuPDF
import base64
from loguru import logger
from typing import Dict, Any, Union
from src.interface import PDFExtractorInterface
from src.constants import OPENAI_API_KEY

class OpenAIVisionExtractor(PDFExtractorInterface):
    def __init__(self, model_name: str):
        """
        Initialize OpenAI Vision extractor with specified model.
        
        Args:
            model_name: OpenAI model name (gpt-4o-mini, gpt-4o, gpt-4-turbo)
        """
        self.model_name = model_name
        self._last_result = None
        self.client = openai.OpenAI(api_key=OPENAI_API_KEY)

    def get_information(self) -> dict:
        return {
            "name": f"OpenAI {self.model_name}",
            "type": "sync",
            "supports": ["text", "image", "structure"],
            "description": f"Extract text from PDFs and images using OpenAI Vision model {self.model_name} with structure preservation."
        }

    def read(self, file_path: str, **kwargs) -> Dict[int, Dict[str, Any]]:
        """
        Extract text from PDF or image using OpenAI Vision API.
        For PDFs, converts each page to image and processes separately.
        """
        page_contents: Dict[int, Dict[str, Any]] = {}

        try:
            if file_path.lower().endswith('.pdf'):
                # Process PDF by converting pages to images
                page_contents = self._process_pdf(file_path)
            else:
                # Process single image
                page_contents = self._process_image(file_path)

        except Exception as e:
            logger.error(f"OpenAI Vision extraction failed: {str(e)}")
            page_contents = {
                1: {
                    "content": {"TEXT": ""},
                    "metadata": {
                        "extractor": f"OpenAI {self.model_name}",
                        "error": str(e)
                    }
                }
            }

        self._last_result = page_contents
        return page_contents

    def _process_pdf(self, file_path: str) -> Dict[int, Dict[str, Any]]:
        """Process PDF by converting each page to image and extracting text."""
        page_contents = {}
        
        try:
            # Open PDF with PyMuPDF
            doc = fitz.open(file_path)
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                
                # Convert page to image
                pix = page.get_pixmap(dpi=200)  # 200 DPI for good quality
                img_bytes = pix.tobytes("png")
                
                # Extract text from this page
                text = self._extract_text_from_image(img_bytes)
                
                page_contents[page_num + 1] = {
                    "content": {"TEXT": text},
                    "metadata": {
                        "extractor": f"OpenAI {self.model_name}",
                        "page_number": page_num + 1,
                        "model": self.model_name
                    }
                }
            
            doc.close()
            
        except Exception as e:
            logger.error(f"Error processing PDF {file_path}: {str(e)}")
            page_contents[1] = {
                "content": {"TEXT": ""},
                "metadata": {
                    "extractor": f"OpenAI {self.model_name}",
                    "error": str(e)
                }
            }
        
        return page_contents

    def _process_image(self, file_path: str) -> Dict[int, Dict[str, Any]]:
        """Process single image file."""
        try:
            with open(file_path, 'rb') as f:
                img_bytes = f.read()
            
            text = self._extract_text_from_image(img_bytes)
            
            return {
                1: {
                    "content": {"TEXT": text},
                    "metadata": {
                        "extractor": f"OpenAI {self.model_name}",
                        "page_number": 1,
                        "model": self.model_name
                    }
                }
            }
        except Exception as e:
            logger.error(f"Error processing image {file_path}: {str(e)}")
            return {
                1: {
                    "content": {"TEXT": ""},
                    "metadata": {
                        "extractor": f"OpenAI {self.model_name}",
                        "error": str(e)
                    }
                }
            }

    def _extract_text_from_image(self, img_bytes: bytes) -> str:
        """Extract text from image bytes using OpenAI Vision API."""
        try:
            # Encode image as base64
            base64_image = base64.b64encode(img_bytes).decode('utf-8')
            
            # Call OpenAI Vision API
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Extract all text from this image preserving structure and formatting. Return only the extracted text."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=4096
            )
            
            text = response.choices[0].message.content
            return text.strip() if text else ""
            
        except Exception as e:
            logger.error(f"OpenAI Vision API error: {str(e)}")
            return f"Error extracting text: {str(e)}"

    def get_status(self, job_id: str) -> str:
        """
        OpenAI Vision is synchronous; extraction always completes immediately.
        """
        return "succeeded"

    def get_result(self, job_id: str) -> Union[str, dict]:
        """
        job_id is unused for sync extractors; returns last result.
        """
        return self._last_result

    def supports_webhook(self) -> bool:
        """
        OpenAI Vision does not support webhooks.
        """
        return False

    def handle_webhook(self, payload: dict) -> Union[str, dict]:
        """
        Webhook handling not supported for OpenAI Vision.
        """
        raise NotImplementedError("OpenAI Vision does not support webhooks")
