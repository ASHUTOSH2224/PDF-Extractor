# src/extractors/textract_extractor.py
import os, uuid, time, logging
from typing import Dict
from botocore.session import get_session
from src.interface import PDFExtractorInterface
from src.constants import AWS_BUCKET_NAME, AWS_REGION

from loguru import logger

class TextractExtractor(PDFExtractorInterface):
    def __init__(self) -> None:
        self.region = AWS_REGION or os.getenv("AWS_REGION") or "us-east-1"
        self._session = None
        self._textract = None
        self._s3 = None
        self._last_result = None

    def _ensure_clients(self) -> None:
        if self._session is None:
            self._session = get_session()  # picks up env/instance creds
        if self._textract is None:
            self._textract = self._session.create_client("textract", region_name=self.region)
        if self._s3 is None:
            self._s3 = self._session.create_client("s3", region_name=self.region)

    def get_information(self) -> dict:
        return {"name": "AWS Textract", "supports": ["Text", "Table"], "mode": "sync-wrapper"}

    def supports_webhook(self) -> bool:
        return False

    def handle_webhook(self, payload: dict) -> dict:
        return {}

    def read(self, file_path: str, **kwargs) -> Dict[int, dict]:
        self._ensure_clients()
        _, ext = os.path.splitext(file_path.lower())
        ext = ext.lstrip(".")

        if ext in {"jpg", "jpeg", "png", "tiff", "tif", "bmp"}:
            with open(file_path, "rb") as f:
                image_bytes = f.read()
            resp = self._textract.detect_document_text(Document={"Bytes": image_bytes})
            result = self._blocks_to_pages(resp.get("Blocks", []))
            self._last_result = result
            return result

        bucket = AWS_BUCKET_NAME or os.getenv("AWS_BUCKET_NAME")
        if not bucket:
            raise RuntimeError("AWS_BUCKET_NAME is not configured for Textract PDF processing")

        key = f"textract-tmp/{uuid.uuid4()}/{os.path.basename(file_path)}"
        try:
            with open(file_path, "rb") as f:
                self._s3.put_object(Bucket=bucket, Key=key, Body=f)

            start = self._textract.start_document_text_detection(
                DocumentLocation={"S3Object": {"Bucket": bucket, "Name": key}}
            )
            job_id = start["JobId"]

            delay = 1.5
            while True:
                res = self._textract.get_document_text_detection(JobId=job_id, MaxResults=1000)
                status = res.get("JobStatus")
                if status == "SUCCEEDED":
                    blocks = res.get("Blocks", []) or []
                    next_token = res.get("NextToken")
                    while next_token:
                        page = self._textract.get_document_text_detection(
                            JobId=job_id, NextToken=next_token, MaxResults=1000
                        )
                        blocks.extend(page.get("Blocks", []) or [])
                        next_token = page.get("NextToken")
                    result = self._blocks_to_pages(blocks)
                    self._last_result = result
                    return result
                if status == "FAILED":
                    raise RuntimeError(f"Textract job failed: {res.get('StatusMessage')}")
                time.sleep(delay)
                delay = min(delay * 1.5, 10.0)
        finally:
            try:
                self._s3.delete_object(Bucket=bucket, Key=key)
            except Exception:
                pass

    @staticmethod
    def _blocks_to_pages(blocks: list) -> Dict[int, dict]:
        page_to_lines: Dict[int, list] = {}
        for b in blocks or []:
            if b.get("BlockType") == "LINE":
                page_num = int(b.get("Page", 1))
                text = (b.get("Text") or "").strip()
                if text:
                    page_to_lines.setdefault(page_num, []).append(text)
        return {p: {"content": {"TEXT": "\n".join(lines)}} for p, lines in page_to_lines.items()}

    def get_status(self, job_id: str) -> str:
        return "succeeded"

    def get_result(self, job_id: str) -> dict:
        return self._last_result or {}
