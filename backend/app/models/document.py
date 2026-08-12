import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship

class Folder(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(unique=True, index=True)
    is_immutable: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    documents: list["DocumentMetadata"] = Relationship(back_populates="folder")

class DocumentMetadata(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    
    title: str
    original_filename: str
    content_type: str
    file_size_bytes: int
    encrypted_file_path: str
    is_locked: bool = Field(default=False)
    
    document_type: str = Field(default="Uncategorized")
    folder_id: Optional[uuid.UUID] = Field(default=None, foreign_key="folder.id")
    folder: Optional[Folder] = Relationship(back_populates="documents")
    
    # NEW: Phase 4 Intelligence Data
    extracted_name: Optional[str] = Field(default=None)
    extracted_dob: Optional[str] = Field(default=None)
    biometric_update_date: Optional[str] = Field(default=None) # Stored as YYYY-MM-DD
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))