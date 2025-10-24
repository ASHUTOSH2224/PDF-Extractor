from pydantic import BaseModel
from typing import Optional, List
from .enums import ExtractionStatus

# Authentication Schemas
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

# Document Schemas
class DocumentResponse(BaseModel):
    uuid: str
    filename: str
    filepath: str
    uploaded_at: str
    page_count: Optional[int]
    file_type: str
    owner_name: Optional[str] = None

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

# Project Schemas
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

# Extraction Schemas
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

# Extractor Schemas
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

# Annotation Schemas
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
    created_at: str
