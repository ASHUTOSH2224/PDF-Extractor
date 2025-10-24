from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, Float, Boolean, ForeignKey, UniqueConstraint
from enum import Enum
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
from .db import Base

class ExtractionStatus(str, Enum):
    NOT_STARTED = "Not Started"
    PROCESSING = "Processing"
    SUCCESS = "Success"
    FAILURE = "Failure"

class PDFExtractorType(str, Enum):
    PYPDF2 = "PyPDF2"
    PYMUPDF = "PyMuPDF"
    PDFPLUMBER = "PDFPlumber"
    CAMELOT = "Camelot"
    TESSERACT = "Tesseract"
    TEXTRACT = "Textract"
    MATHPIX = "Mathpix"
    TABULA = "Tabula"
    UNSTRUCTURED = "Unstructured"
    OPENAI_GPT4O_MINI = "gpt-4o-mini"
    OPENAI_GPT4O = "gpt-4o"
    OPENAI_GPT4_TURBO = "gpt-4-turbo"
    MARKITDOWN = "MarkItDown"
    LLAMAPARSE = "LlamaParse"

class ImageExtractorType(str, Enum):
    TESSERACT = "Tesseract"
    TEXTRACT = "Textract"
    MATHPIX = "Mathpix"
    OPENAI_GPT4O_MINI = "gpt-4o-mini"
    OPENAI_GPT4O = "gpt-4o"
    OPENAI_GPT4_TURBO = "gpt-4-turbo"

class FeedbackType(str, Enum):
    SINGLE = "Single"
    COMPARISON = "Comparison"

class DocumentResponse(BaseModel):
    uuid: str
    filename: str
    filepath: str
    uploaded_at: str
    page_count: Optional[int]
    file_type: str
    owner_name: Optional[str] = None

class ProjectResponse(BaseModel):
    uuid: str
    name: str
    description: Optional[str] = None
    created_at: str
    owner_name: Optional[str] = None
    file_upload_type: Optional[str] = None  # 'pdf' or 'image'
    is_owner: Optional[bool] = None

class ProjectCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    file_upload_type: str  # 'pdf' or 'image'

class DocumentExtractionJobResponse(BaseModel):
    uuid: str
    document_uuid: str
    extractor: str
    status: ExtractionStatus
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    latency_ms: Optional[int] = None
    cost: Optional[float] = None
    pages_annotated: int = 0  # Number of pages with feedback
    total_rating: Optional[float] = None  # Average rating across all pages
    total_feedback_count: int = 0  # Total number of feedback entries

class DocumentPageFeedbackResponse(BaseModel):
    uuid: str
    document_uuid: str
    page_number: int
    extraction_job_uuid: str
    feedback_type: str
    rating: Optional[int] = None
    comment: Optional[str] = None
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    created_at: str

class DocumentPageContentResponse(BaseModel):
    uuid: str
    extraction_job_uuid: str
    page_number: int
    content: dict
    feedback: Optional[DocumentPageFeedbackResponse] = None

class DocumentPageFeedbackRequest(BaseModel):
    document_uuid: str
    page_number: int
    extraction_job_uuid: str
    rating: Optional[int] = None  # 1-5 rating
    comment: Optional[str] = None

class UploadResponse(BaseModel):
    message: str
    document_uuid: str

class MultipleUploadResponse(BaseModel):
    message: str
    document_uuids: List[str]
    failed_uploads: List[dict] = []

class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total_count: int
    total_pages: int
    has_next: bool
    has_previous: bool

class PaginatedDocumentsResponse(BaseModel):
    documents: List[DocumentResponse]
    pagination: PaginationMeta

class Token(BaseModel):
    access_token: str
    token_type: str

class UserCreate(BaseModel):
    email: str
    password: str
    name: str

class UserLogin(BaseModel):
    email: str
    password: str

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

class ExtractorInfo(BaseModel):
    id: str
    name: str
    description: str
    cost_per_page: float
    support_tags: List[str] = []

class ExtractorCategory(BaseModel):
    category: str
    extractors: List[ExtractorInfo]

class ExtractorsResponse(BaseModel):
    pdf_extractors: List[ExtractorCategory]
    image_extractors: List[ExtractorCategory]

class UploadWithExtractorsRequest(BaseModel):
    selected_extractors: List[str]

class Document(Base):
    __tablename__ = "documents"
    
    uuid = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    page_count = Column(Integer, nullable=True)
    file_type = Column(String, nullable=False)  # 'pdf' or 'image'
    project_uuid = Column(String, nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    owner_name = Column(String, nullable=True)
    deleted_at = Column(DateTime, nullable=True, index=True)  # Soft delete timestamp

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    # New fields for approval workflow and roles
    is_approved = Column(Boolean, default=False)
    role = Column(String, nullable=False, default="user")  # 'admin' or 'user'
    name = Column(String, nullable=True)
    last_login = Column(DateTime, nullable=True)
    # Optional org metadata (non-breaking, nullable)
    organization_name = Column(String, nullable=True)
    organization_id = Column(String, nullable=True, index=True)

class Project(Base):
    __tablename__ = "projects"

    uuid = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    owner_name = Column(String, nullable=True)
    file_upload_type = Column(String, nullable=True)  # 'pdf' or 'image'
    deleted_at = Column(DateTime, nullable=True, index=True)  # Soft delete timestamp

class DocumentExtractionJob(Base):
    __tablename__ = "document_extraction_jobs"
    
    uuid = Column(String, primary_key=True, index=True)
    document_uuid = Column(String, nullable=False, index=True)
    extractor = Column(String, nullable=False)
    status = Column(String, nullable=False, default=ExtractionStatus.NOT_STARTED)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    latency_ms = Column(Integer, nullable=True)  # latency in milliseconds
    cost = Column(Float, nullable=True)  # total cost
    deleted_at = Column(DateTime, nullable=True, index=True)  # Soft delete timestamp

class DocumentPageContent(Base):
    __tablename__ = "document_page_content"
    
    uuid = Column(String, primary_key=True, index=True)
    extraction_job_uuid = Column(String, nullable=False, index=True)
    page_number = Column(Integer, nullable=False)
    content = Column(JSON, nullable=False)
    metadata_ = Column(JSON, default=dict)
    deleted_at = Column(DateTime, nullable=True, index=True)  # Soft delete timestamp
    
    __table_args__ = (
        {'extend_existing': True},
    )

class DocumentPageFeedback(Base):
    __tablename__ = "document_page_feedback"
    
    uuid = Column(String, primary_key=True, index=True)
    document_uuid = Column(String, nullable=False, index=True)
    page_number = Column(Integer, nullable=False, index=True)
    extraction_job_uuid = Column(String, nullable=False, index=True)
    feedback_type = Column(String, nullable=False, default="single")
    rating = Column(Integer, nullable=True)  # 1-5 rating
    comment = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    user_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    deleted_at = Column(DateTime, nullable=True, index=True)  # Soft delete timestamp
    
    __table_args__ = (
        UniqueConstraint(
            'document_uuid', 
            'page_number', 
            'extraction_job_uuid', 
            'user_id',
            name='uq_user_page_extractor_rating'
        ),
        {'extend_existing': True},
    )

# --- Annotations ---
class Annotation(Base):
    __tablename__ = "annotations"

    uuid = Column(String, primary_key=True, index=True)
    document_uuid = Column(String, index=True, nullable=False)
    extraction_job_uuid = Column(String, index=True, nullable=False)
    page_number = Column(Integer, index=True, nullable=False)
    text = Column(Text, nullable=False)
    comment = Column(Text, nullable=False)
    selection_start = Column(Integer, nullable=False)
    selection_end = Column(Integer, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    user_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    deleted_at = Column(DateTime, nullable=True, index=True)  # Soft delete timestamp

class AnnotationCreateRequest(BaseModel):
    # Match frontend payload keys
    documentId: str
    extractionJobUuid: str
    pageNumber: int
    text: str
    comment: str | None = None
    selectionStart: int
    selectionEnd: int

class AnnotationResponse(BaseModel):
    uuid: str
    document_uuid: str
    extraction_job_uuid: str
    page_number: int
    text: str
    comment: str
    selection_start: int
    selection_end: int
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    created_at: str

class UserRatingBreakdown(BaseModel):
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    average_rating: float
    pages_rated: int
    total_ratings: int
    latest_comment: Optional[str] = None
    latest_rated_at: str

class AnnotationListItem(BaseModel):
    uuid: str
    page_number: int
    extractor: str
    extraction_job_uuid: str
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    text: str
    comment: str
    created_at: str