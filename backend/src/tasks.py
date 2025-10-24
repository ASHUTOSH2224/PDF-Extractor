import os
import time
import uuid
from celery import Celery
from sqlalchemy import create_engine, update
from sqlalchemy.orm import sessionmaker
from loguru import logger
from contextlib import contextmanager
from datetime import datetime, timezone
from src.constants import (
    EXTRACTOR_RETRY_CONFIG,
    DEFAULT_RETRY_CONFIG,
    REDIS_BROKER_URL,
    REDIS_BACKEND_URL,
    DATABASE_URL,
    CIRCUIT_BREAKER_THRESHOLD,
)
from src.file_coordinator import (
    download_to_shared_volume,
    mark_task_complete,
    mark_task_failed,
    redis_client,
)
from sqlalchemy.exc import DatabaseError, OperationalError, PendingRollbackError
from psycopg2 import DatabaseError as Psycopg2DatabaseError
from src.factory import get_reader
from src.models.database import Document, DocumentExtractionJob, DocumentPageContent
from src.models.enums import ExtractionStatus

# Configure Celery
celery_app = Celery("pdf_extraction")
celery_app.config_from_object(
    {
        "broker_url": REDIS_BROKER_URL,
        "result_backend": REDIS_BACKEND_URL,
        "task_serializer": "json",
        "accept_content": ["json"],
        "result_serializer": "json",
        "timezone": "UTC",
        "enable_utc": True,
    }
)

# Create synchronous database engine for Celery tasks
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_timeout=30,
    echo=False,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db_session():
    """Get database session for Celery tasks"""
    return SessionLocal()


@contextmanager
def get_db_session_context():
    """Get database session with automatic cleanup and rollback for Celery tasks"""
    session = SessionLocal()
    try:
        yield session
    except Exception:
        # Rollback transaction on any error
        try:
            session.rollback()
            logger.debug("Transaction rolled back after error")
        except Exception as rollback_err:
            logger.warning(f"Error during rollback: {rollback_err}")
        raise
    finally:
        try:
            session.close()
            logger.debug("Database session closed successfully")
        except Exception as e:
            logger.warning(f"Error closing database session: {e}")
        # DO NOT dispose engine here - it's shared across all tasks


def calculate_extraction_cost(extractor_type: str, page_count: int) -> float:
    """Calculate cost based on extractor type and page count"""
    # Cost per page for different extractors (example rates)
    cost_per_page = {
        # PDF extractors
        "PyPDF": 0.0,
        "PyMuPDF": 0.0,
        "PDFPlumber": 0.0,
        "Camelot": 0.0,
        # Image extractors
        "Textract": 0.0015,  # AWS Textract pricing
        "Tesseract": 0.0,  # Free OCR
        # OpenAI Vision models
        "gpt-4o-mini": 0.005,  # OpenAI GPT-4o-mini pricing
        "gpt-4o": 0.010,  # OpenAI GPT-4o pricing
        "gpt-4-turbo": 0.015,  # OpenAI GPT-4-turbo pricing
    }

    base_cost = cost_per_page.get(extractor_type, 0.001)
    return round(base_cost * page_count, 4)


def get_retry_config(extractor_type: str) -> dict:
    """Get retry configuration based on extractor type"""
    return EXTRACTOR_RETRY_CONFIG.get(extractor_type, DEFAULT_RETRY_CONFIG)


def is_infrastructure_error(exception: Exception) -> bool:
    """Determine if error is infrastructure-related (don't retry)"""
    infrastructure_errors = (
        DatabaseError,
        OperationalError,
        PendingRollbackError,  # Add this
        Psycopg2DatabaseError,
        ConnectionError,
        FileNotFoundError,
        OSError,
    )
    return isinstance(exception, infrastructure_errors)


def check_circuit_breaker(extractor_type: str) -> bool:
    """Check if circuit breaker is open for this extractor"""
    circuit_key = f"circuit_breaker:{extractor_type}"
    failure_count = redis_client.get(circuit_key)
    if failure_count and int(failure_count) >= CIRCUIT_BREAKER_THRESHOLD:
        logger.warning(f"Circuit breaker OPEN for {extractor_type} - too many failures")
        return True
    return False


def record_extractor_failure(extractor_type: str):
    """Record failure for circuit breaker tracking"""
    from .file_coordinator import redis_client
    from .constants import CIRCUIT_BREAKER_TIMEOUT

    circuit_key = f"circuit_breaker:{extractor_type}"
    redis_client.incr(circuit_key)
    redis_client.expire(circuit_key, CIRCUIT_BREAKER_TIMEOUT)


def reset_circuit_breaker(extractor_type: str):
    """Reset circuit breaker on success"""
    from .file_coordinator import redis_client

    circuit_key = f"circuit_breaker:{extractor_type}"
    redis_client.delete(circuit_key)


@celery_app.task(bind=True)
def process_document_with_extractor(
    self, job_uuid: str, document_uuid: str, file_path: str, extractor_type: str
):
    """
    Process a document with the specified extractor (sync or async).
    """
    start_time = datetime.now(timezone.utc)
    temp_file_path = None
    with get_db_session_context() as db:
        try:
            # Check circuit breaker before processing
            if check_circuit_breaker(extractor_type):
                raise RuntimeError(
                    f"Circuit breaker is OPEN for {extractor_type}. "
                    f"Too many recent failures. Try again later."
                )
            # Update job status to Processing
            db.execute(
                update(DocumentExtractionJob)
                .where(DocumentExtractionJob.uuid == job_uuid)
                .values(status=ExtractionStatus.PROCESSING, start_time=start_time)
            )
            db.commit()
            # --- 1. Conditional file retrieval based on storage type ---
            local_file_path = None
            temp_file_path = None
            # Get document info from database to determine storage type
            # Use query() method for better session management
            document = db.query(Document).filter(Document.uuid == document_uuid).first()
            if not document:
                raise RuntimeError(f"Document {document_uuid} not found")
            # Check if file is stored in S3 (starts with "projects/") or locally
            if file_path.startswith("projects/"):
                # Use shared volume coordination for S3 files
                shared_path = download_to_shared_volume(
                    document_uuid, file_path, document.filename
                )
                local_file_path = shared_path
                temp_file_path = None  # Don't track as temp (managed by coordinator)
                logger.info(f"Using shared volume file: {shared_path}")
            elif os.path.exists(file_path):
                # File is stored locally
                logger.info(f"Using existing local file: {file_path}")
                local_file_path = file_path
            else:
                # File not found in either location
                raise RuntimeError(f"File not found: {file_path}")
            # --- 2. Get the right reader ---
            reader = get_reader(extractor_type)  # from your factory.py
            # --- 3. Start extraction ---
            result_or_job_id = reader.read(local_file_path)
            # --- 3. Handle sync vs async ---
            if reader.supports_webhook():
                # You would normally not poll here; webhook handler will call back later
                # For Celery job, you might just exit early and let webhook handler finish DB update
                page_contents = None
            else:
                if isinstance(result_or_job_id, dict):  # sync reader returned results
                    page_contents = result_or_job_id
                else:
                    job_id = result_or_job_id
                    # Poll until job finishes
                    status = reader.get_status(job_id)
                    while status not in ["succeeded", "failed"]:
                        logger.info(f"Job {job_id} status: {status}, retrying...")
                        time.sleep(5)
                        status = reader.get_status(job_id)

                    if status == "failed":
                        raise RuntimeError(f"Extraction failed for job {job_id}")
                    page_contents = reader.get_result(job_id)

            # --- 4. Validate and save page contents to DB ---
            def _has_meaningful_content(pages):
                try:
                    if not pages:
                        return False
                    for _p, body in pages.items():
                        data = (body or {}).get("content", {})
                        text = (
                            data.get("COMBINED")
                            or data.get("TEXT")
                            or data.get("LATEX")
                            or ""
                        ).strip()
                        if text:
                            return True
                    return False
                except Exception:
                    return False

            if not _has_meaningful_content(page_contents):
                raise RuntimeError(
                    f"No meaningful content extracted by {extractor_type}"
                )
            if page_contents:
                try:
                    print(
                        f"Extractor {extractor_type} produced {len(page_contents)} pages; sample keys: {list(next(iter(page_contents.values())).get('content', {}).keys()) if page_contents else []}"
                    )
                except Exception:
                    pass
                for page_num, content in page_contents.items():
                    page_content = DocumentPageContent(
                        uuid=str(uuid.uuid4()),
                        extraction_job_uuid=job_uuid,
                        page_number=page_num,
                        content=content["content"],
                    )
                    db.add(page_content)
            # --- 5. Latency & cost ---
            end_time = datetime.now(timezone.utc)
            latency_ms = int((end_time - start_time).total_seconds() * 1000)
            cost = calculate_extraction_cost(
                extractor_type, len(page_contents) if page_contents else 0
            )
            # --- 6. Update job status ---
            db.execute(
                update(DocumentExtractionJob)
                .where(DocumentExtractionJob.uuid == job_uuid)
                .values(
                    status=ExtractionStatus.SUCCESS,
                    end_time=end_time,
                    latency_ms=latency_ms,
                    cost=cost,
                )
            )
            db.commit()
            logger.info(
                f"Successfully processed document {document_uuid} with {extractor_type}"
            )
            # Reset circuit breaker on success
            reset_circuit_breaker(extractor_type)
            # Mark task complete and cleanup if needed
            mark_task_complete(document_uuid, job_uuid)
        except Exception as e:
            # Failure path
            end_time = datetime.now(timezone.utc)
            latency_ms = int((end_time - start_time).total_seconds() * 1000)
            # CRITICAL: Rollback any pending transaction before attempting failure update
            try:
                db.rollback()
                logger.debug("Transaction rolled back in exception handler")
            except Exception as rb_err:
                logger.warning(f"Error rolling back transaction: {rb_err}")
            # Attempt to update job status to FAILURE
            try:
                db.execute(
                    update(DocumentExtractionJob)
                    .where(DocumentExtractionJob.uuid == job_uuid)
                    .values(
                        status=ExtractionStatus.FAILURE,
                        end_time=end_time,
                        latency_ms=latency_ms,
                        cost=0.0,
                    )
                )
                db.commit()
            except Exception as db_err:
                logger.error(f"Failed to update job status to FAILURE: {db_err}")
                # Continue with failure handling even if DB update fails
            # Record failure for circuit breaker
            record_extractor_failure(extractor_type)
            # Check if infrastructure error - fail immediately
            if is_infrastructure_error(e):
                logger.error(
                    f"Infrastructure failure for {extractor_type} - NOT RETRYING: {str(e)}"
                )
                mark_task_failed(document_uuid, job_uuid)
                raise  # Don't retry infrastructure errors
            logger.error(
                f"Failed to process document {document_uuid} with {extractor_type}: {str(e)}"
            )
            logger.error(f"Error type: {type(e).__name__}")
            if hasattr(e, "__cause__"):
                logger.error(
                    f"Caused by: {type(e.__cause__).__name__}: {str(e.__cause__)}"
                )
            mark_task_failed(document_uuid, job_uuid)
            # Get extractor-specific retry config
            retry_config = get_retry_config(extractor_type)
            raise self.retry(
                exc=e,
                countdown=retry_config["countdown"],
                max_retries=retry_config["max_retries"],
            )
        finally:
            # Note: Shared volume files are managed by file_coordinator
            # Only cleanup temp files from old S3 download logic
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                    logger.info(f"Cleaned up temporary file: {temp_file_path}")
                except Exception as e:
                    logger.warning(
                        f"Failed to clean up temporary file {temp_file_path}: {e}"
                    )
