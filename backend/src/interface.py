
from typing import Union
from abc import ABC, abstractmethod

class PDFExtractorInterface(ABC):

    @abstractmethod
    def get_information(self) -> dict:
        """
        Get information about the extractor.
        """
        pass
    
    @abstractmethod
    def read(self, file_path: str, **kwargs) -> Union[str, dict]:
        """
        Trigger extraction from a PDF.
        - For sync libs (e.g., PyPDF2, Textract, Tabula): run and return extracted text/data immediately.
        - For async APIs (e.g., LlamaParse, OpenAI, Gemini): kick off a job and return a job_id or result depending on mode.
        """
        pass

    @abstractmethod
    def get_status(self, job_id: str) -> str:
        """
        For async APIs, check the processing status.
        Returns one of: ['pending', 'running', 'succeeded', 'failed'].
        For sync libs, return 'succeeded' immediately.
        """
        pass

    @abstractmethod
    def get_result(self, job_id: str) -> Union[str, dict]:
        """
        Fetch the final parsed output once status == succeeded.
        For sync libs, this is just the immediate output from `read`.
        """
        pass

    @abstractmethod
    def supports_webhook(self) -> bool:
        """
        Return True if the provider supports webhook callbacks (e.g., LlamaParse API).
        False for local libs or APIs without webhook support.
        """
        pass

    @abstractmethod
    def handle_webhook(self, payload: dict) -> Union[str, dict]:
        """
        Process an incoming webhook payload (for async providers that push results).
        Return standardized parsed output.
        No-op for sync libs.
        """
        pass