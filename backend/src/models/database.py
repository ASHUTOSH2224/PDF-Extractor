from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, Float, Boolean, ForeignKey
from datetime import datetime, timezone
from ..db import Base
from .enums import ExtractionStatus

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
    last_login = Column(DateTime(timezone=True), nullable=True)
    # Optional org metadata (non-breaking, nullable)
    organization_name = Column(String, nullable=True)
    organization_id = Column(String, nullable=True, index=True)

class Project(Base):
    __tablename__ = "projects"

    uuid = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    owner_name = Column(String, nullable=True)
    file_upload_type = Column(String, nullable=True)  # 'pdf' or 'image'
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)  # Soft delete timestamp

class Document(Base):
    __tablename__ = "documents"
    
    uuid = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    uploaded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    page_count = Column(Integer, nullable=True)
    file_type = Column(String, nullable=False)  # 'pdf' or 'image'
    project_uuid = Column(String, nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    owner_name = Column(String, nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)  # Soft delete timestamp

class DocumentExtractionJob(Base):
    __tablename__ = "document_extraction_jobs"
    
    uuid = Column(String, primary_key=True, index=True)
    document_uuid = Column(String, nullable=False, index=True)
    extractor = Column(String, nullable=False)
    status = Column(String, nullable=False, default=ExtractionStatus.NOT_STARTED)
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    latency_ms = Column(Integer, nullable=True)  # latency in milliseconds
    cost = Column(Float, nullable=True)  # total cost
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)  # Soft delete timestamp

class DocumentPageContent(Base):
    __tablename__ = "document_page_content"
    
    uuid = Column(String, primary_key=True, index=True)
    extraction_job_uuid = Column(String, nullable=False, index=True)
    page_number = Column(Integer, nullable=False)
    content = Column(JSON, nullable=False)
    metadata_ = Column(JSON, default=dict)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)  # Soft delete timestamp
    
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
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)  # Soft delete timestamp
    
    __table_args__ = (
        {'extend_existing': True},
    )

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
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)  # Soft delete timestamp
