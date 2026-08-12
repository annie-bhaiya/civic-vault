from pydantic import BaseModel, Field
from typing import Optional

class ImageEditRequest(BaseModel):
    crop_x: Optional[int] = None
    crop_y: Optional[int] = None
    crop_width: Optional[int] = None
    crop_height: Optional[int] = None
    resize_width: Optional[int] = None
    resize_height: Optional[int] = None
    target_format: Optional[str] = Field(default=None)
    quality: int = Field(default=85, ge=1, le=100)
    save_as_new: bool = Field(default=True)
    
    # NEW: The Smart Size Constraint
    target_size_kb: Optional[int] = Field(default=None, description="Force file below this size in KB")

class PdfCompressRequest(BaseModel):
    mode: str = Field(default="standard")
    password: Optional[str] = Field(default=None)
    
    # NEW: The Smart Size Constraint
    target_size_kb: Optional[int] = Field(default=None, description="Force file below this size in KB")

class DocumentRenameRequest(BaseModel):
    title: str = Field(...)

class PdfLockRequest(BaseModel):
    password: str = Field(...)

class FolderCreateRequest(BaseModel):
    name: str = Field(..., description="The name of the new folder")

class FolderRenameRequest(BaseModel):
    name: str = Field(..., description="The new name for the folder")

class WatermarkRequest(BaseModel):
    text: str = Field(..., description="The text to stamp on the document")
    password: Optional[str] = Field(default=None, description="Unlock password if PDF is protected")