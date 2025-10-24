from fastapi import Depends, FastAPI, File, UploadFile, HTTPException, Form
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.openapi.models import OpenAPI
from sqlalchemy import select, delete, update, or_, func
from typing import List, Optional, Dict, Any
import uuid
import aioboto3
import json
import logging
import PyPDF2
import math
import os
from pathlib import Path
from datetime import datetime, timezone

from .db import get_db, engine_async, Base
from .models import (
    Document,
    DocumentExtractionJob,
    DocumentPageContent,
    DocumentPageFeedback,
    DocumentResponse,
    DocumentExtractionJobResponse,
    DocumentPageContentResponse,
    DocumentPageFeedbackRequest,
    DocumentPageFeedbackResponse,
    Project,
    ProjectCreateRequest,
    ExtractorCategory,
    ExtractorInfo,
    ExtractorsResponse,
    ExtractionStatus,
    PDFExtractorType,
    ImageExtractorType,
    ProjectResponse,
    User,
    MultipleUploadResponse,
    PaginationMeta,
    PaginatedDocumentsResponse,
    Annotation,
    AnnotationCreateRequest,
    AnnotationResponse,
    UserRatingBreakdown,
    AnnotationListItem,
)
from src.tasks import process_document_with_extractor
from src.auth.routes import router as auth_router
from src.auth.security import get_current_user
from src.constants import AWS_BUCKET_NAME, AWS_REGION

logger = logging.getLogger(__name__)


def to_utc_isoformat(dt: datetime) -> str:
    """
    Convert a datetime to ISO format string with UTC timezone.
    Handles both timezone-aware and naive datetimes.
    Naive datetimes are assumed to be UTC.
    """
    if dt is None:
        return None
    # If datetime is naive (no timezone info), assume it's UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    # Convert to UTC if it's in a different timezone
    elif dt.tzinfo != timezone.utc:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat()

# Resolve project root and uploads directory absolutely so static mount works
# main.py lives in backend/src; the repo root is two levels up
PROJECT_ROOT = Path(__file__).resolve().parents[2]


async def start_background_tasks_for_documents(
    db: AsyncSession, 
    document_data: List[Dict[str, Any]], 
    selected_extractor_list: List[str]
) -> None:
    """
    Start background extraction tasks for uploaded documents.
    
    Args:
        db: Database session
        document_data: List of dictionaries containing document info (uuid, file_type, file_path)
        selected_extractor_list: List of selected extractor names
    """
    for doc_info in document_data:
        document_uuid = doc_info["uuid"]
        file_type = doc_info["file_type"]
        file_path = doc_info["file_path"]
        
        # Determine extractors for this file type
        if file_type == "pdf":
            file_extractors = [
                extractor.value for extractor in PDFExtractorType
            ]
        else:  # image
            file_extractors = [
                extractor.value for extractor in ImageExtractorType
            ]
        
        # Use selected extractors if provided, otherwise use all for file type
        if selected_extractor_list:
            # Filter selected extractors to only include those valid for this file type
            file_extractors = [ext for ext in selected_extractor_list if ext in file_extractors]
        
        # Create extraction jobs for selected extractors
        extraction_jobs = []
        for extractor_name in file_extractors:
            job_uuid = str(uuid.uuid4())
            extraction_job = DocumentExtractionJob(
                uuid=job_uuid,
                document_uuid=document_uuid,
                extractor=extractor_name,
                status=ExtractionStatus.NOT_STARTED,
            )
            db.add(extraction_job)
            extraction_jobs.append(extraction_job)
        # Register all tasks in Redis before starting
        from src.file_coordinator import register_extraction_tasks
        from src.constants import FILE_CLEANUP_TTL_SECONDS
        
        job_uuids = [job.uuid for job in extraction_jobs]
        register_extraction_tasks(
            document_uuid, 
            job_uuids, 
            FILE_CLEANUP_TTL_SECONDS
        )
        
        # Start background tasks for each extractor
        for job in extraction_jobs:
            process_document_with_extractor.delay(
                job.uuid, document_uuid, str(file_path), job.extractor
            )

async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events"""
    logger.info("Starting application - initializing database...")
    
    try:
        # Create database tables
        async with engine_async.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")
        # Create admin user if it doesn't exist
        async for db in get_db():
            from .auth.security import hash_password
            from .constants import ADMIN_NAME, ADMIN_EMAIL, ADMIN_PASSWORD
            
            try:
                result = await db.execute(select(User).where(User.email == ADMIN_EMAIL))
                admin_user = result.scalar_one_or_none()
                
                if not admin_user and ADMIN_EMAIL and ADMIN_PASSWORD:
                    admin_user = User(
                        name=ADMIN_NAME or "Admin",
                        email=ADMIN_EMAIL,
                        hashed_password=hash_password(ADMIN_PASSWORD),
                        is_active=True,
                        is_approved=True,
                        role='admin'
                    )
                    db.add(admin_user)
                    await db.commit()
                    logger.info(f"Created admin user: {ADMIN_EMAIL}")
                elif admin_user:
                    logger.info(f"Admin user already exists: {ADMIN_EMAIL}")
                else:
                    logger.warning("Admin credentials not configured - skipping admin user creation")
            except Exception as e:
                logger.error(f"Error checking/creating admin user: {e}")
                # Don't fail startup if admin user creation fails
            break
            
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise
    
    yield  # Application runs
    
    logger.info("Shutting down - disposing database connections...")
    await engine_async.dispose()


# app = FastAPI(lifespan=lifespan)


# custom_openapi = OpenAPI(
#     openapi="3.0.0",  # Correct version field
#     info={
#         "title": "Custom API",
#         "version": "1.0.0",
#     },
#     paths={},
#     components={},
#     servers=[],
# )

app = FastAPI(
    title="My API",
    description="A FastAPI boilerplate with common features",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    openapi_version="3.0.3"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=False,  # Must be False when using "*"
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],  # Simplify this too
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])

# Expose uploaded files only in development for convenience
if STAGE == "development":
    app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")


@app.get("/")
async def root():
    return {"message": "PDF Extraction Tool", "version": "1.0.0"}

# In your FastAPI app
@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "PDF Extraction Tool is running"}


@app.get("/extractors", response_model=ExtractorsResponse)
async def get_extractors():
    """Get available extractors grouped by category for PDF and Image files"""
    from .factory import READER_MAP
    from .models import PDFExtractorType, ImageExtractorType
    
    def get_extractor_info(extractor_type: str) -> ExtractorInfo:
        """Get extractor information from the actual extractor instance"""
        try:
            extractor_instance = READER_MAP[extractor_type]()
            info = extractor_instance.get_information()
            
            # Map the extractor info to our response format
            return ExtractorInfo(
                id=extractor_type,
                name=info.get("name", extractor_type),
                description=info.get("description", f"Extract content using {extractor_type}"),
                cost_per_page=0.0,  # Could be enhanced to get from extractor info
                support_tags=info.get("supports", ["Text"]),
            )
        except Exception as e:
            logger.warning(f"Failed to get info for extractor {extractor_type}: {e}")
            # Fallback if extractor fails to initialize
            return ExtractorInfo(
                id=extractor_type,
                name=extractor_type,
                description=f"Extract content using {extractor_type}",
                cost_per_page=0.0,
                support_tags=["Text"],
            )
    
    # Get available PDF extractors from factory
    available_pdf_extractors = []
    for extractor_type in PDFExtractorType:
        if extractor_type.value in READER_MAP:
            available_pdf_extractors.append(get_extractor_info(extractor_type.value))
    
    # Get available Image extractors from factory
    available_image_extractors = []
    for extractor_type in ImageExtractorType:
        if extractor_type.value in READER_MAP:
            available_image_extractors.append(get_extractor_info(extractor_type.value))
    
    # Define category mappings
    python_based_ids = {"PyPDF2", "PyMuPDF", "PDFPlumber", "Camelot", "MarkItDown", "Unstructured", "Tabula"}
    ocr_ids = {"Tesseract", "Textract", "Mathpix", "LlamaParse"}
    llm_vision_ids = {"gpt-4o-mini", "gpt-4o", "gpt-4-turbo"}
    
    # Group PDF extractors by category
    pdf_extractors = [
        ExtractorCategory(
            category="Python Based",
            extractors=[ext for ext in available_pdf_extractors if ext.id in python_based_ids]
        ),
        ExtractorCategory(
            category="OCR",
            extractors=[ext for ext in available_pdf_extractors if ext.id in ocr_ids]
        ),
        ExtractorCategory(
            category="LLM Vision",
            extractors=[ext for ext in available_pdf_extractors if ext.id in llm_vision_ids]
        ),
    ]
    
    # Group Image extractors by category
    image_extractors = [
        ExtractorCategory(
            category="OCR",
            extractors=[ext for ext in available_image_extractors if ext.id in ocr_ids]
        ),
        ExtractorCategory(
            category="LLM Vision",
            extractors=[ext for ext in available_image_extractors if ext.id in llm_vision_ids]
        ),
    ]
    
    # Filter out empty categories
    pdf_extractors = [cat for cat in pdf_extractors if cat.extractors]
    image_extractors = [cat for cat in image_extractors if cat.extractors]
    
    return ExtractorsResponse(
        pdf_extractors=pdf_extractors, 
        image_extractors=image_extractors
    )


@app.post("/projects/{project_uuid}/upload-multiple", response_model=MultipleUploadResponse)
async def upload_multiple_documents(
    project_uuid: str,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db, use_cache=True),
    user: User = Depends(get_current_user, use_cache=True),
    selected_extractors: str = Form("")
):
    """
    Upload multiple PDF or image files and create documents with extraction jobs for all extractors
    """
    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required")
    
    document_uuids = []
    failed_uploads = []
    document_data = []  # Store document info for background task creation
    
    # Parse selected extractors once
    try:
        if selected_extractors:
            selected_extractor_list = json.loads(selected_extractors)
        else:
            # Default to all PDF extractors (will be adjusted per file)
            selected_extractor_list = [
                extractor.value for extractor in PDFExtractorType
            ]
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400, detail="Invalid selected_extractors format"
        )
    
    # Phase 1: Upload all files and create document records
    for file in files:
        try:
            if file.filename is None:
                failed_uploads.append({
                    "filename": "unknown",
                    "error": "File name is required"
                })
                continue
                
            # Validate file type and determine file type
            filename_lower = file.filename.lower()
            if filename_lower.endswith(".pdf"):
                file_type = "pdf"
            elif filename_lower.endswith(
                (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp")
            ):
                file_type = "image"
            else:
                failed_uploads.append({
                    "filename": file.filename,
                    "error": "Only PDF and image files are allowed"
                })
                continue
            
            # Generate unique document UUID
            document_uuid = str(uuid.uuid4())
            
            # Read once for validation
            content = await file.read()
            MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20MB
            if len(content) > MAX_UPLOAD_BYTES:
                failed_uploads.append({
                    "filename": file.filename,
                    "error": "File too large (max 20MB)"
                })
                continue
                
            if file_type == 'pdf' and not content.startswith(b'%PDF'):
                failed_uploads.append({
                    "filename": file.filename,
                    "error": "Invalid PDF file"
                })
                continue

            # Conditional storage based on S3 availability
            if is_s3_available():
                # S3 available - store only in S3
                s3_key = f"projects/{project_uuid}/documents/{document_uuid}/v1/{file.filename}"
                
                # Upload to S3
                session = aioboto3.Session()
                async with session.client("s3", region_name=AWS_REGION) as s3:
                    await s3.put_object(
                        Bucket=AWS_BUCKET_NAME,
                        Key=s3_key,
                        Body=content,
                    )
                
                # Store S3 key in database instead of local path
                filepath = s3_key
                file_path = None  # No local file path
                logger.info(f"File stored in S3: {s3_key}")
                
            else:
                # No S3 - store locally
                file_path = UPLOADS_DIR / f"{document_uuid}_{file.filename}"
                filename_on_disk = file_path.name
                
                # Save locally
                with open(file_path, "wb") as buffer:
                    buffer.write(content)
                
                # Store local path in database
                filepath = str(Path("uploads") / filename_on_disk)
                logger.info(f"File stored locally: {file_path}")
                
            # Count pages based on file type
            if file_type == "pdf":
                page_count = None
                try:
                    # Use content directly for page counting (works for both S3 and local)
                    from io import BytesIO
                    pdf_reader = PyPDF2.PdfReader(BytesIO(content))
                    page_count = len(pdf_reader.pages)
                except Exception as e:
                    logger.warning(f"Could not count pages for {file.filename}: {str(e)}")
            else:  # image
                page_count = 1  # Images are treated as single-page documents
                
            # Create document record
            document = Document(
                uuid=document_uuid,
                filename=file.filename,
                filepath=filepath,
                page_count=page_count,
                file_type=file_type,
                project_uuid=project_uuid,
                user_id=user.id,
                owner_name=user.name,
            )
            db.add(document)
            
            # Store document info for background task creation
            document_data.append({
                "uuid": document_uuid,
                "file_type": file_type,
                "file_path": filepath  # Use the stored path (S3 key or local path)
            })
            
            document_uuids.append(document_uuid)
                
        except Exception as e:
            failed_uploads.append({
                "filename": file.filename,
                "error": f"Error processing file: {str(e)}"
            })
            # Clean up local file if it was created (only for local storage)
            if 'file_path' in locals() and file_path and file_path.exists():
                file_path.unlink()
    
    # Phase 2: Commit all successful uploads to database
    await db.commit()
    
    # Phase 3: Start background tasks for all successfully uploaded documents
    if document_data:
        await start_background_tasks_for_documents(db, document_data, selected_extractor_list)
        await db.commit()  # Commit the extraction jobs
    
    return MultipleUploadResponse(
        message=f"Successfully uploaded {len(document_uuids)} files. {len(failed_uploads)} files failed.",
        document_uuids=document_uuids,
        failed_uploads=failed_uploads,
    )

@app.post("/create-project", response_model=ProjectResponse)
async def create_project(project: ProjectCreateRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        project_uuid = str(uuid.uuid4())
        new_project = Project(
            uuid=project_uuid,
            name=project.name,
            description=project.description,
            user_id=user.id,
            owner_name=user.name,
            file_upload_type=project.file_upload_type
        )
        db.add(new_project)
        await db.commit()
        await db.refresh(new_project)
        return ProjectResponse(
            uuid=new_project.uuid,
            name=new_project.name,
            description=new_project.description,
            created_at=to_utc_isoformat(new_project.created_at),
            owner_name=new_project.owner_name,
            file_upload_type=new_project.file_upload_type,
            is_owner=True
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to create project: {str(e)}"
        )


@app.get("/projects", response_model=List[ProjectResponse])
async def list_projects(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    # Show all projects regardless of owner, excluding deleted projects
    result = await db.execute(select(Project).where(Project.deleted_at.is_(None)).order_by(Project.created_at.desc()))
    projects = result.scalars().all()
    return [
        ProjectResponse(
            uuid=p.uuid,
            name=p.name,
            description=p.description,
            created_at=to_utc_isoformat(p.created_at),
            owner_name=p.owner_name,
            file_upload_type=p.file_upload_type,
            is_owner=(p.user_id == user.id)
        ) for p in projects
    ]



@app.get("/projects/{project_uuid}", response_model=ProjectResponse)
async def get_project(project_uuid: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    # Allow any user to view any project, excluding deleted projects
    result = await db.execute(select(Project).where(Project.uuid == project_uuid, Project.deleted_at.is_(None)))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse(
        uuid=p.uuid,
        name=p.name,
        description=p.description,
        created_at=to_utc_isoformat(p.created_at),
        owner_name=p.owner_name,
        file_upload_type=p.file_upload_type,
        is_owner=(p.user_id == user.id)
    )

@app.delete("/delete-project/{project_uuid}")
async def delete_project(project_uuid: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    # Soft delete: mark project as deleted instead of removing from database
    try:
        # Only the owner (creator) can delete the project
        result = await db.execute(select(Project).where(Project.uuid == project_uuid, Project.deleted_at.is_(None)))
        p = result.scalar_one_or_none()
        if not p:
            raise HTTPException(status_code=404, detail="Project not found")
        if p.user_id != user.id:
            raise HTTPException(status_code=403, detail="Only the project owner can delete this project")
        
        # Set deleted_at timestamp instead of hard delete
        p.deleted_at = datetime.now(timezone.utc)
        await db.commit()
        return {"message": "Project deleted"}
    except HTTPException:
        raise
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete project")


@app.get("/projects/{project_uuid}/documents", response_model=PaginatedDocumentsResponse)
async def list_project_documents(
    project_uuid: str, 
    page: int = 1, 
    page_size: int = 10,
    sort_by: str = "uploaded_at",
    sort_direction: str = "desc",
    db: AsyncSession = Depends(get_db), 
    user: User = Depends(get_current_user)
):
    """
    List documents in a project with pagination and sorting.
    
    Args:
        project_uuid: Project identifier
        page: Page number (1-based, default: 1)
        page_size: Number of documents per page (default: 10)
        sort_by: Field to sort by. Valid options: uploaded_at, filename, file_type, page_count, owner_name, uuid (default: uploaded_at)
        sort_direction: Sort direction. Valid options: asc, desc (default: desc)
        
    Returns:
        PaginatedDocumentsResponse: Contains documents list and pagination metadata
        
    Raises:
        HTTPException: 404 if project not found
        HTTPException: 400 if invalid pagination or sorting parameters
    """
    # Verify that the project exists (visible to all users), excluding deleted projects
    project_result = await db.execute(select(Project).where(Project.uuid == project_uuid, Project.deleted_at.is_(None)))
    if not project_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    # Validate pagination parameters
    if page < 1:
        raise HTTPException(status_code=400, detail="Page must be greater than 0")

    # Validate sorting parameters
    valid_sort_fields = ["uploaded_at", "filename", "file_type", "page_count", "owner_name", "uuid"]
    if sort_by not in valid_sort_fields:
        raise HTTPException(status_code=400, detail=f"Invalid sort field. Must be one of: {', '.join(valid_sort_fields)}")
    
    if sort_direction not in ["asc", "desc"]:
        raise HTTPException(status_code=400, detail="Sort direction must be 'asc' or 'desc'")

    # Get total count efficiently
    count_result = await db.execute(
        select(func.count(Document.uuid)).where(
            Document.project_uuid == project_uuid,
            Document.deleted_at.is_(None)
        )
    )
    total_count = count_result.scalar()

    # Calculate pagination metadata
    total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
    offset = (page - 1) * page_size

    # Build dynamic sorting
    sort_column = getattr(Document, sort_by)
    if sort_direction == "desc":
        order_clause = sort_column.desc()
    else:
        order_clause = sort_column.asc()

    # Get paginated documents
    result = await db.execute(
        select(Document)
        .where(
            Document.project_uuid == project_uuid,
            Document.deleted_at.is_(None)
        )
        .order_by(order_clause)
        .offset(offset)
        .limit(page_size)
    )
    docs = result.scalars().all()

    # Build response
    documents = [
        DocumentResponse(
            uuid=str(doc.uuid),
            filename=str(doc.filename),
            filepath=str(doc.filepath),
            uploaded_at=to_utc_isoformat(doc.uploaded_at),
            page_count=int(doc.page_count) if doc.page_count else None,
            file_type=str(doc.file_type),
            owner_name=doc.owner_name,
        )
        for doc in docs
    ]

    pagination = PaginationMeta(
        page=page,
        page_size=page_size,
        total_count=total_count,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1
    )

    return PaginatedDocumentsResponse(
        documents=documents,
        pagination=pagination
    )


@app.get(
    "/projects/{project_uuid}/documents/{document_uuid}",
    response_model=DocumentResponse,
)
async def get_document(
    project_uuid: str,
    document_uuid: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get document details by UUID within a project"""
    result = await db.execute(
        select(Document).where(
            Document.uuid == document_uuid, 
            Document.project_uuid == project_uuid,
            Document.deleted_at.is_(None)
        )
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentResponse(
        uuid=str(document.uuid),
        filename=str(document.filename),
        filepath=str(document.filepath),
        uploaded_at=to_utc_isoformat(document.uploaded_at),
        page_count=int(document.page_count),
        file_type=str(document.file_type),
        owner_name=document.owner_name,
    )


@app.delete("/projects/{project_uuid}/documents/{document_uuid}")
async def delete_document(
    project_uuid: str,
    document_uuid: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Soft delete a document and all related data. Only the project owner can delete."""
    # Verify project exists and requester is owner, excluding deleted projects
    project_result = await db.execute(select(Project).where(Project.uuid == project_uuid, Project.deleted_at.is_(None)))
    project = project_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.user_id != user.id:
        raise HTTPException(status_code=403, detail="Only the project owner can delete files")

    # Fetch document within project, excluding already deleted documents
    doc_result = await db.execute(
        select(Document).where(
            Document.uuid == document_uuid, 
            Document.project_uuid == project_uuid,
            Document.deleted_at.is_(None)
        )
    )
    document = doc_result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Collect job UUIDs for cascading soft deletions
    jobs_result = await db.execute(
        select(DocumentExtractionJob.uuid).where(
            DocumentExtractionJob.document_uuid == document_uuid,
            DocumentExtractionJob.deleted_at.is_(None)
        )
    )
    job_uuid_rows = jobs_result.all()
    job_uuids = [row[0] for row in job_uuid_rows]

    try:
        # Soft delete related rows instead of hard delete
        current_time = datetime.now(timezone.utc)
        
        if job_uuids:
            await db.execute(
                update(DocumentPageContent)
                .where(DocumentPageContent.extraction_job_uuid.in_(job_uuids))
                .values(deleted_at=current_time)
            )
        
        await db.execute(
            update(DocumentPageFeedback)
            .where(DocumentPageFeedback.document_uuid == document_uuid)
            .values(deleted_at=current_time)
        )
        
        await db.execute(
            update(Annotation)
            .where(Annotation.document_uuid == document_uuid)
            .values(deleted_at=current_time)
        )
        
        await db.execute(
            update(DocumentExtractionJob)
            .where(DocumentExtractionJob.document_uuid == document_uuid)
            .values(deleted_at=current_time)
        )
        
        # Soft delete the document itself
        await db.execute(
            update(Document)
            .where(Document.uuid == document_uuid)
            .values(deleted_at=current_time)
        )

        # Note: We keep the files (S3 and local) for potential recovery
        # Files can be cleaned up later by a separate cleanup job if needed

        await db.commit()
        return {"message": "Document deleted"}
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        await db.rollback()
        logger.error(f"Error deleting document {document_uuid}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete document")


@app.delete("/delete-document/{document_uuid}")
async def delete_document_legacy(
    document_uuid: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Legacy soft delete endpoint to support older clients. Only project owner can delete."""
    # Fetch document to determine project, excluding already deleted documents
    doc_result = await db.execute(select(Document).where(Document.uuid == document_uuid, Document.deleted_at.is_(None)))
    document = doc_result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    project_uuid = document.project_uuid
    project_result = await db.execute(select(Project).where(Project.uuid == project_uuid, Project.deleted_at.is_(None)))
    project = project_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.user_id != user.id:
        raise HTTPException(status_code=403, detail="Only the project owner can delete files")

    # Collect job UUIDs for cascading soft deletions
    jobs_result = await db.execute(
        select(DocumentExtractionJob.uuid).where(
            DocumentExtractionJob.document_uuid == document_uuid,
            DocumentExtractionJob.deleted_at.is_(None)
        )
    )
    job_uuid_rows = jobs_result.all()
    job_uuids = [row[0] for row in job_uuid_rows]

    try:
        # Soft delete related rows instead of hard delete
        current_time = datetime.now(timezone.utc)
        
        if job_uuids:
            await db.execute(
                update(DocumentPageContent)
                .where(DocumentPageContent.extraction_job_uuid.in_(job_uuids))
                .values(deleted_at=current_time)
            )
        
        await db.execute(
            update(DocumentPageFeedback)
            .where(DocumentPageFeedback.document_uuid == document_uuid)
            .values(deleted_at=current_time)
        )
        
        await db.execute(
            update(Annotation)
            .where(Annotation.document_uuid == document_uuid)
            .values(deleted_at=current_time)
        )
        
        await db.execute(
            update(DocumentExtractionJob)
            .where(DocumentExtractionJob.document_uuid == document_uuid)
            .values(deleted_at=current_time)
        )
        
        # Soft delete the document itself
        await db.execute(
            update(Document)
            .where(Document.uuid == document_uuid)
            .values(deleted_at=current_time)
        )

        # Note: We keep the files (S3 and local) for potential recovery
        # Files can be cleaned up later by a separate cleanup job if needed

        await db.commit()
        return {"message": "Document deleted"}
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        await db.rollback()
        logger.error(f"Error deleting document {document_uuid}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete document")


@app.get(
    "/projects/{project_uuid}/documents/{document_uuid}/extraction-jobs",
    response_model=List[DocumentExtractionJobResponse],
)
async def get_document_extraction_jobs(
    project_uuid: str,
    document_uuid: str,
    filter_by_user: bool = False,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get all extraction jobs for a document with feedback statistics
    
    Args:
        filter_by_user: If True, only show ratings from the current user
    """
    # First verify that the document belongs to the project (visible to all users)
    doc_result = await db.execute(
        select(Document).where(
            Document.uuid == document_uuid, 
            Document.project_uuid == project_uuid,
            Document.deleted_at.is_(None)
        )
    )
    if not doc_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Document not found")

    result = await db.execute(
        select(DocumentExtractionJob)
        .where(
            DocumentExtractionJob.document_uuid == document_uuid,
            DocumentExtractionJob.deleted_at.is_(None)
        )
        .order_by(DocumentExtractionJob.extractor)
    )
    jobs = result.scalars().all()

    # Get feedback statistics for each job
    job_responses = []
    for job in jobs:
        # Get all feedback for this extraction job, optionally filtered by user
        feedback_query = select(DocumentPageFeedback).where(
            DocumentPageFeedback.extraction_job_uuid == job.uuid,
            DocumentPageFeedback.deleted_at.is_(None)
        )
        
        # Apply user filter if requested
        if filter_by_user:
            feedback_query = feedback_query.where(
                DocumentPageFeedback.user_id == user.id
            )
        
        feedback_result = await db.execute(feedback_query)
        feedbacks = feedback_result.scalars().all()

        # Calculate statistics
        total_feedback_count = len(feedbacks)
        pages_annotated = len(
            set(f.page_number for f in feedbacks if f.rating is not None)
        )

        # Calculate average rating
        ratings = [f.rating for f in feedbacks if f.rating is not None]
        total_rating = round(sum(ratings) / len(ratings), 2) if ratings else None

        job_responses.append(
            DocumentExtractionJobResponse(
                uuid=str(job.uuid),
                document_uuid=str(job.document_uuid),
                extractor=str(job.extractor),
                status=ExtractionStatus(job.status),
                start_time=to_utc_isoformat(job.start_time) if job.start_time else None,
                end_time=to_utc_isoformat(job.end_time) if job.end_time else None,
                latency_ms=int(job.latency_ms or 0),
                cost=float(job.cost or 0.0),
                pages_annotated=pages_annotated,
                total_rating=total_rating,
                total_feedback_count=total_feedback_count,
            )
        )
    return job_responses


@app.get(
    "/projects/{project_uuid}/documents/{document_uuid}/extraction-jobs/{job_uuid}/pages",
    response_model=List[DocumentPageContentResponse],
)
async def get_extraction_job_pages(
    project_uuid: str,
    document_uuid: str,
    job_uuid: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get all pages for an extraction job"""
    # First verify that the extraction job belongs to a document owned by the user and project
    job_result = await db.execute(
        select(DocumentExtractionJob).where(
            DocumentExtractionJob.uuid == job_uuid,
            DocumentExtractionJob.deleted_at.is_(None)
        )
    )
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Extraction job not found")
    
    doc_result = await db.execute(
        select(Document).where(
            Document.uuid == document_uuid, 
            Document.project_uuid == project_uuid,
            Document.deleted_at.is_(None)
        )
    )
    if not doc_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Document not found")
    result = await db.execute(
        select(DocumentPageContent)
        .where(
            DocumentPageContent.extraction_job_uuid == job_uuid,
            DocumentPageContent.deleted_at.is_(None)
        )
        .order_by(DocumentPageContent.page_number)
    )
    pages = result.scalars().all()
    return [
        DocumentPageContentResponse(
            uuid=str(page.uuid),
            extraction_job_uuid=str(page.extraction_job_uuid),
            page_number=int(page.page_number),
            content=dict(page.content),
        )
        for page in pages
    ]


@app.get(
    "/projects/{project_uuid}/documents/{document_uuid}/pages/{page_number}/extractions",
    response_model=List[DocumentPageContentResponse],
)
async def get_page_extractions(
    project_uuid: str,
    document_uuid: str,
    page_number: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get all extraction results for a specific page across all extractors"""
    # First verify that the document belongs to the user and project
    doc_result = await db.execute(
        select(Document).where(
            Document.uuid == document_uuid, 
            Document.project_uuid == project_uuid,
            Document.deleted_at.is_(None)
        )
    )
    if not doc_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Document not found")
    # Get all extraction jobs for this document
    jobs_result = await db.execute(
        select(DocumentExtractionJob).where(
            DocumentExtractionJob.document_uuid == document_uuid,
            DocumentExtractionJob.deleted_at.is_(None)
        )
    )
    jobs = jobs_result.scalars().all()
    # Get page content for this specific page from all extraction jobs
    page_contents = []
    for job in jobs:
        result = await db.execute(
            select(DocumentPageContent).where(
                DocumentPageContent.extraction_job_uuid == job.uuid,
                DocumentPageContent.page_number == page_number,
                DocumentPageContent.deleted_at.is_(None)
            )
        )
        page_content = result.scalar_one_or_none()
        if page_content:
            page_contents.append(page_content)
    # Get feedback for this page
    feedback_result = await db.execute(
        select(DocumentPageFeedback).where(
            DocumentPageFeedback.document_uuid == document_uuid,
            DocumentPageFeedback.page_number == page_number,
            DocumentPageFeedback.deleted_at.is_(None)
        )
    )
    feedbacks = feedback_result.scalars().all()
    # Create a mapping of extraction_job_uuid to feedback
    feedback_map = {f.extraction_job_uuid: f for f in feedbacks}
    return [
        DocumentPageContentResponse(
            uuid=str(page.uuid),
            extraction_job_uuid=str(page.extraction_job_uuid),
            page_number=int(page.page_number),
            content=dict(page.content),
            feedback=DocumentPageFeedbackResponse(
                uuid=str(feedback.uuid),
                document_uuid=str(feedback.document_uuid),
                page_number=int(feedback.page_number),
                extraction_job_uuid=str(feedback.extraction_job_uuid),
                feedback_type=str(feedback.feedback_type),
                rating=int(feedback.rating),
                comment=str(feedback.comment),
                created_at=to_utc_isoformat(feedback.created_at),
            )
            if feedback
            else None,
        )
        for page in page_contents
        for feedback in [feedback_map.get(page.extraction_job_uuid)]
    ]


@app.post(
    "/projects/{project_uuid}/documents/{document_uuid}/feedback",
    response_model=DocumentPageFeedbackResponse,
)
async def submit_feedback(
    project_uuid: str,
    document_uuid: str,
    feedback: DocumentPageFeedbackRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Submit feedback for a specific page extraction"""
    try:
        # First verify that the document exists in the given project (accessible to any user)
        doc_result = await db.execute(
            select(Document).where(
                Document.uuid == feedback.document_uuid, 
                Document.project_uuid == project_uuid,
                Document.deleted_at.is_(None)
            )
        )
        if not doc_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Document not found")
        # Check if feedback already exists for this page, extractor, and user
        existing_feedback = await db.execute(
            select(DocumentPageFeedback).where(
                DocumentPageFeedback.document_uuid == feedback.document_uuid,
                DocumentPageFeedback.page_number == feedback.page_number,
                DocumentPageFeedback.extraction_job_uuid
                == feedback.extraction_job_uuid,
                DocumentPageFeedback.user_id == user.id,
                DocumentPageFeedback.deleted_at.is_(None)
            )
        )
        existing = existing_feedback.scalar_one_or_none()
        if existing:
            # Update existing feedback
            if feedback.rating is not None:
                existing.rating = feedback.rating
            if feedback.comment is not None:
                existing.comment = feedback.comment
            # Update user info
            existing.user_id = user.id
            existing.user_name = user.name
        else:
            # Create new feedback
            feedback_uuid = str(uuid.uuid4())
            new_feedback = DocumentPageFeedback(
                uuid=feedback_uuid,
                document_uuid=feedback.document_uuid,
                page_number=feedback.page_number,
                extraction_job_uuid=feedback.extraction_job_uuid,
                feedback_type="single",
                rating=feedback.rating,
                comment=feedback.comment,
                user_id=user.id,
                user_name=user.name,
            )
            db.add(new_feedback)
        await db.commit()
        # Return the updated/created feedback
        if existing:
            return DocumentPageFeedbackResponse(
                uuid=str(existing.uuid),
                document_uuid=str(existing.document_uuid),
                page_number=int(existing.page_number),
                extraction_job_uuid=str(existing.extraction_job_uuid),
                feedback_type=str(existing.feedback_type),
                rating=int(existing.rating),
                comment=str(existing.comment),
                user_id=existing.user_id,
                user_name=existing.user_name,
                created_at=to_utc_isoformat(existing.created_at),
            )
        else:
            # Refresh to get the created object
            await db.refresh(new_feedback)
            return DocumentPageFeedbackResponse(
                uuid=str(new_feedback.uuid),
                document_uuid=str(new_feedback.document_uuid),
                page_number=int(new_feedback.page_number),
                extraction_job_uuid=str(new_feedback.extraction_job_uuid),
                feedback_type=str(new_feedback.feedback_type),
                rating=int(new_feedback.rating),
                comment=str(new_feedback.comment),
                user_id=new_feedback.user_id,
                user_name=new_feedback.user_name,
                created_at=to_utc_isoformat(new_feedback.created_at),
            )

    except Exception as e:
        logger.error(f"Error submitting feedback: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to submit feedback")


@app.get(
    "/projects/{project_uuid}/documents/{document_uuid}/pages/{page_number}/feedback",
    response_model=List[DocumentPageFeedbackResponse],
)
async def get_page_feedback(
    project_uuid: str,
    document_uuid: str,
    page_number: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get all feedback for a specific page"""
    try:
        # Verify that the document belongs to the project (visible to all users)
        doc_result = await db.execute(
            select(Document).where(
                Document.uuid == document_uuid, 
                Document.project_uuid == project_uuid,
                Document.deleted_at.is_(None)
            )
        )
        if not doc_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Document not found")
        result = await db.execute(
            select(DocumentPageFeedback).where(
                DocumentPageFeedback.document_uuid == document_uuid,
                DocumentPageFeedback.page_number == page_number,
                DocumentPageFeedback.deleted_at.is_(None)
            )
        )
        feedbacks = result.scalars().all()
        return [
            DocumentPageFeedbackResponse(
                uuid=str(feedback.uuid),
                document_uuid=str(feedback.document_uuid),
                page_number=int(feedback.page_number),
                extraction_job_uuid=str(feedback.extraction_job_uuid),
                feedback_type=str(feedback.feedback_type),
                rating=int(feedback.rating),
                comment=str(feedback.comment),
                user_id=feedback.user_id,
                user_name=feedback.user_name,
                created_at=to_utc_isoformat(feedback.created_at),
            )
            for feedback in feedbacks
        ]
    except Exception as e:
        logger.error(f"Error getting page feedback: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get page feedback")


@app.get(
    "/projects/{project_uuid}/documents/{document_uuid}/extraction-jobs/{job_uuid}/rating-breakdown",
    response_model=List[UserRatingBreakdown],
)
async def get_rating_breakdown(
    project_uuid: str,
    document_uuid: str,
    job_uuid: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get user-wise rating breakdown for an extraction job"""
    try:
        # Verify document exists in project
        doc_result = await db.execute(
            select(Document).where(
                Document.uuid == document_uuid,
                Document.project_uuid == project_uuid,
                Document.deleted_at.is_(None)
            )
        )
        if not doc_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Verify extraction job exists
        job_result = await db.execute(
            select(DocumentExtractionJob).where(
                DocumentExtractionJob.uuid == job_uuid,
                DocumentExtractionJob.document_uuid == document_uuid,
                DocumentExtractionJob.deleted_at.is_(None)
            )
        )
        if not job_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Extraction job not found")
        
        # Get all feedback for this extraction job, grouped by user
        feedback_result = await db.execute(
            select(DocumentPageFeedback).where(
                DocumentPageFeedback.extraction_job_uuid == job_uuid,
                DocumentPageFeedback.deleted_at.is_(None)
            ).order_by(DocumentPageFeedback.created_at.desc())
        )
        feedbacks = feedback_result.scalars().all()
        
        # Group by user
        user_feedback_map: Dict[Optional[int], List] = {}
        for feedback in feedbacks:
            user_id = feedback.user_id
            if user_id not in user_feedback_map:
                user_feedback_map[user_id] = []
            user_feedback_map[user_id].append(feedback)
        
        # Build breakdown
        breakdown = []
        for user_id, user_feedbacks in user_feedback_map.items():
            ratings = [f.rating for f in user_feedbacks if f.rating is not None]
            if not ratings:
                continue
            
            avg_rating = sum(ratings) / len(ratings)
            pages_rated = len(set(f.page_number for f in user_feedbacks))
            latest = user_feedbacks[0]  # Already sorted by created_at desc
            
            breakdown.append(UserRatingBreakdown(
                user_id=user_id,
                user_name=latest.user_name or "Unknown User",
                average_rating=round(avg_rating, 2),
                pages_rated=pages_rated,
                total_ratings=len(ratings),
                latest_comment=latest.comment,
                latest_rated_at=to_utc_isoformat(latest.created_at),
            ))
        
        return breakdown
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting rating breakdown: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get rating breakdown")


@app.get(
    "/projects/{project_uuid}/documents/{document_uuid}/pages/{page_number}/average-rating",
)
async def get_page_average_rating(
    project_uuid: str,
    document_uuid: str,
    page_number: int,
    extraction_job_uuid: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get average rating for a specific page and extractor across all users"""
    try:
        # Verify document exists in project
        doc_result = await db.execute(
            select(Document).where(
                Document.uuid == document_uuid,
                Document.project_uuid == project_uuid,
                Document.deleted_at.is_(None)
            )
        )
        if not doc_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Get all ratings for this page and specific extractor
        feedback_result = await db.execute(
            select(DocumentPageFeedback).where(
                DocumentPageFeedback.document_uuid == document_uuid,
                DocumentPageFeedback.page_number == page_number,
                DocumentPageFeedback.extraction_job_uuid == extraction_job_uuid,
                DocumentPageFeedback.rating.isnot(None),
                DocumentPageFeedback.deleted_at.is_(None)
            )
        )
        feedbacks = feedback_result.scalars().all()
        
        if not feedbacks:
            return {
                "average_rating": None,
                "total_ratings": 0,
                "user_rating": None
            }
        
        ratings = [f.rating for f in feedbacks]
        average_rating = round(sum(ratings) / len(ratings), 2)
        
        # Get current user's rating for this page and extractor
        user_rating = None
        for feedback in feedbacks:
            if feedback.user_id == user.id:
                user_rating = feedback.rating
                break
        
        return {
            "average_rating": average_rating,
            "total_ratings": len(ratings),
            "user_rating": user_rating
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting page average rating: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get page average rating")


@app.get(
    "/projects/{project_uuid}/documents/{document_uuid}/annotations-list",
    response_model=List[AnnotationListItem],
)
async def get_annotations_list(
    project_uuid: str,
    document_uuid: str,
    extractor_uuid: Optional[str] = None,
    user_id: Optional[int] = None,
    page_number: Optional[int] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all annotations for a document with filters"""
    try:
        # Verify document exists in project
        doc_result = await db.execute(
            select(Document).where(
                Document.uuid == document_uuid,
                Document.project_uuid == project_uuid,
                Document.deleted_at.is_(None)
            )
        )
        if not doc_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Build query with filters
        query = select(Annotation, DocumentExtractionJob).join(
            DocumentExtractionJob,
            Annotation.extraction_job_uuid == DocumentExtractionJob.uuid
        ).where(
            Annotation.document_uuid == document_uuid,
            Annotation.deleted_at.is_(None),
            DocumentExtractionJob.deleted_at.is_(None)
        )
        
        if extractor_uuid:
            query = query.where(Annotation.extraction_job_uuid == extractor_uuid)
        if user_id is not None:
            query = query.where(Annotation.user_id == user_id)
        if page_number is not None:
            query = query.where(Annotation.page_number == page_number)
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    Annotation.text.ilike(search_pattern),
                    Annotation.comment.ilike(search_pattern)
                )
            )
        
        query = query.order_by(Annotation.page_number.asc(), Annotation.created_at.desc())
        
        result = await db.execute(query)
        rows = result.all()
        
        return [
            AnnotationListItem(
                uuid=str(annotation.uuid),
                page_number=int(annotation.page_number),
                extractor=job.extractor,
                extraction_job_uuid=str(annotation.extraction_job_uuid),
                user_id=annotation.user_id,
                user_name=annotation.user_name or "Unknown User",
                text=str(annotation.text),
                comment=str(annotation.comment),
                created_at=to_utc_isoformat(annotation.created_at),
            )
            for annotation, job in rows
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting annotations list: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get annotations list")


# Robust, auth-protected download endpoint that serves files from S3
@app.get("/projects/{project_uuid}/documents/{document_uuid}/pdf-load")
async def download_document_file(project_uuid: str, document_uuid: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    # Allow any authenticated user to download within the same project context
    result = await db.execute(
        select(Document).where(
            Document.uuid == document_uuid, 
            Document.project_uuid == project_uuid,
            Document.deleted_at.is_(None)
        )
    )
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Conditional file serving based on storage type
    if document.filepath.startswith("projects/"):
        # File is stored in S3
        try:
            # Download file from S3
            session = aioboto3.Session()
            async with session.client("s3", region_name=AWS_REGION) as s3:
                response = await s3.get_object(
                    Bucket=AWS_BUCKET_NAME,
                    Key=document.filepath,
                )
                
                # Read the file content
                file_content = await response['Body'].read()
                
                # Return the file as a streaming response
                from fastapi.responses import Response
                return Response(
                    content=file_content,
                    media_type="application/pdf",
                    headers={
                        "Content-Disposition": f"inline; filename={document.filename}",
                        "Content-Length": str(len(file_content))
                    }
                )
                
        except Exception as e:
            logger.error(f"Error downloading file from S3: {e}")
            raise HTTPException(status_code=404, detail="File not found on server")
    else:
        # File is stored locally
        try:
            local_file_path = UPLOADS_DIR / document.filepath.replace("uploads/", "")
            if not os.path.exists(local_file_path):
                raise HTTPException(status_code=404, detail="File not found")
            
            with open(local_file_path, "rb") as f:
                content = f.read()
                from fastapi.responses import Response
                return Response(
                    content=content,
                    media_type="application/pdf",
                    headers={
                        "Content-Disposition": f"inline; filename={document.filename}",
                        "Content-Length": str(len(content))
                    }
                )
        except Exception as e:
            logger.error(f"Error reading local file: {e}")
            raise HTTPException(status_code=404, detail="File not found on server")

# -------------------- Annotations API --------------------
@app.post("/api/annotations", response_model=AnnotationResponse)
async def create_annotation(
    payload: AnnotationCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        # Ensure document exists (visible to all users)
        doc_result = await db.execute(
            select(Document).where(
                Document.uuid == payload.documentId,
                Document.deleted_at.is_(None)
            )
        )
        doc = doc_result.scalar_one_or_none()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        # Ensure extraction job exists and belongs to the same document
        job_result = await db.execute(
            select(DocumentExtractionJob).where(
                DocumentExtractionJob.uuid == payload.extractionJobUuid,
                DocumentExtractionJob.deleted_at.is_(None)
            )
        )
        job = job_result.scalar_one_or_none()
        if not job or job.document_uuid != payload.documentId:
            raise HTTPException(status_code=404, detail="Extraction job not found for document")

        anno_uuid = str(uuid.uuid4())
        anno = Annotation(
            uuid=anno_uuid,
            document_uuid=payload.documentId,
            extraction_job_uuid=payload.extractionJobUuid,
            page_number=int(payload.pageNumber),
            text=payload.text,
            comment=payload.comment or "",
            selection_start=int(payload.selectionStart),
            selection_end=int(payload.selectionEnd),
            user_id=user.id,
            user_name=user.name,
        )
        db.add(anno)
        await db.commit()
        await db.refresh(anno)
        return AnnotationResponse(
            uuid=str(anno.uuid),
            document_uuid=str(anno.document_uuid),
            extraction_job_uuid=str(anno.extraction_job_uuid),
            page_number=int(anno.page_number),
            text=str(anno.text),
            comment=str(anno.comment),
            selection_start=int(anno.selection_start),
            selection_end=int(anno.selection_end),
            user_id=anno.user_id,
            user_name=anno.user_name,
            created_at=to_utc_isoformat(anno.created_at),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating annotation: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create annotation")


@app.get("/api/annotations", response_model=List[AnnotationResponse])
async def list_annotations(
    documentId: str,
    extractionJobUuid: str | None = None,
    pageNumber: int | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        # Ensure document exists
        doc_result = await db.execute(
            select(Document).where(
                Document.uuid == documentId,
                Document.deleted_at.is_(None)
            )
        )
        if not doc_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Document not found")

        query = select(Annotation).where(
            Annotation.document_uuid == documentId,
            Annotation.deleted_at.is_(None)
        )
        if extractionJobUuid:
            query = query.where(Annotation.extraction_job_uuid == extractionJobUuid)
        if pageNumber is not None:
            query = query.where(Annotation.page_number == pageNumber)
        query = query.order_by(Annotation.created_at.asc())

        result = await db.execute(query)
        annos = result.scalars().all()
        return [
            AnnotationResponse(
                uuid=str(a.uuid),
                document_uuid=str(a.document_uuid),
                extraction_job_uuid=str(a.extraction_job_uuid),
                page_number=int(a.page_number),
                text=str(a.text),
                comment=str(a.comment),
                selection_start=int(a.selection_start),
                selection_end=int(a.selection_end),
                user_id=a.user_id,
                user_name=a.user_name,
                created_at=to_utc_isoformat(a.created_at),
            )
            for a in annos
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing annotations: {e}")
        raise HTTPException(status_code=500, detail="Failed to list annotations")


@app.delete("/api/annotations/{annotation_uuid}")
async def delete_annotation(
    annotation_uuid: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        # Find annotation excluding already deleted ones
        result = await db.execute(
            select(Annotation).where(
                Annotation.uuid == annotation_uuid,
                Annotation.deleted_at.is_(None)
            )
        )
        anno = result.scalar_one_or_none()
        if not anno:
            raise HTTPException(status_code=404, detail="Annotation not found")
        
        # Soft delete the annotation
        await db.execute(
            update(Annotation)
            .where(Annotation.uuid == annotation_uuid)
            .values(deleted_at=datetime.now(timezone.utc))
        )
        await db.commit()
        return {"message": "Annotation deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting annotation: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete annotation")


@app.post(
    "/projects/{project_uuid}/documents/{document_uuid}/extraction-jobs/{job_uuid}/retry",
    response_model=dict
)
async def retry_extraction_job(
    project_uuid: str,
    document_uuid: str,
    job_uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retry a failed extraction job"""
    try:
        # Verify project ownership, excluding deleted projects
        project_result = await db.execute(
            select(Project).where(
                Project.uuid == project_uuid,
                Project.user_id == current_user.id,
                Project.deleted_at.is_(None)
            )
        )
        project = project_result.scalar_one_or_none()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Verify document ownership
        doc_result = await db.execute(
            select(Document).where(
                Document.uuid == document_uuid,
                Document.project_uuid == project_uuid,
                Document.deleted_at.is_(None)
            )
        )
        document = doc_result.scalar_one_or_none()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Get the extraction job
        job_result = await db.execute(
            select(DocumentExtractionJob).where(
                DocumentExtractionJob.uuid == job_uuid,
                DocumentExtractionJob.document_uuid == document_uuid,
                DocumentExtractionJob.deleted_at.is_(None)
            )
        )
        job = job_result.scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail="Extraction job not found")

        # Only allow retry for failed jobs
        if job.status not in [ExtractionStatus.FAILURE, "Failed"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot retry job with status: {job.status}"
            )

        # Reset job status and clear previous results
        job.status = ExtractionStatus.NOT_STARTED
        job.start_time = None
        job.end_time = None
        job.latency_ms = None
        job.cost = None

        # Soft delete existing page content for this job
        await db.execute(
            update(DocumentPageContent)
            .where(DocumentPageContent.extraction_job_uuid == job_uuid)
            .values(deleted_at=datetime.now(timezone.utc))
        )

        await db.commit()

        # Queue the retry task
        try:
            from src.tasks import process_document_with_extractor
            process_document_with_extractor.delay(
                job_uuid, 
                document_uuid, 
                document.filepath, 
                job.extractor
            )
            logger.info(f"Successfully queued retry task for job {job_uuid}")
        except Exception as task_err:
            logger.error(f"Failed to queue retry task: {task_err}")
            # Still return success since the job status was reset
            # The job can be manually retried later

        return {
            "message": "Extraction job retry initiated",
            "job_uuid": job_uuid,
            "status": "NOT_STARTED"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrying extraction job: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Exception details: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to retry extraction job: {str(e)}")