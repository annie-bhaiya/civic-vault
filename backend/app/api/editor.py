import os
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.db.session import get_db
from app.models.document import DocumentMetadata, Folder
from app.services.vault import VaultService
from app.services.editor import DocumentEditorService
from app.schemas.editor import ImageEditRequest, PdfCompressRequest, PdfLockRequest, WatermarkRequest

router = APIRouter(prefix="/editor", tags=["Editor"])

def get_derived_folder_id(db: Session, original_folder_id: uuid.UUID) -> uuid.UUID:
    """
    Checks if the source folder is immutable. 
    If so, routes the new file to the 'Processed & Exported' folder to keep the source clean.
    """
    if not original_folder_id:
        return None
        
    folder = db.get(Folder, original_folder_id)
    if folder and folder.is_immutable:
        processed_folder = db.exec(select(Folder).where(Folder.name == "Processed & Exported")).first()
        return processed_folder.id if processed_folder else original_folder_id
        
    return original_folder_id

@router.post("/{doc_id}/image", response_model=DocumentMetadata)
def edit_image(
    doc_id: uuid.UUID,
    params: ImageEditRequest, 
    db: Session = Depends(get_db)
):
    raw_bytes, metadata = VaultService.retrieve_document(db=db, doc_id=doc_id)
    if not metadata.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Document is not an image.")

    try:
        processed_bytes, new_mime, new_ext = DocumentEditorService.process_image(raw_bytes, params)
    except ValueError as ve:
        # Catch our new constraint validations
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image processing failed: {str(e)}")

    base_name = os.path.splitext(metadata.original_filename)[0]
    new_filename = f"{base_name}_edited{new_ext}"
    target_folder_id = get_derived_folder_id(db, metadata.folder_id)
    
    return VaultService.save_bytes(
        db=db,
        file_bytes=processed_bytes,
        original_filename=new_filename,
        content_type=new_mime,
        title=f"{metadata.title} (Edited)",
        folder_id=target_folder_id
    )

@router.post("/{doc_id}/compress-pdf", response_model=DocumentMetadata)
def compress_pdf(
    doc_id: uuid.UUID,
    params: PdfCompressRequest,
    db: Session = Depends(get_db)
):
    raw_bytes, metadata = VaultService.retrieve_document(db=db, doc_id=doc_id)
    if metadata.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Document is not a PDF.")

    try:
        processed_bytes, new_mime, new_ext = DocumentEditorService.compress_pdf(
            raw_bytes, 
            mode=params.mode, 
            password=params.password, 
            target_size_kb=params.target_size_kb
        )
    except ValueError as ve:
        # Route password errors to 403, and size constraint errors to 400
        if "password" in str(ve).lower() or "locked" in str(ve).lower():
            raise HTTPException(status_code=403, detail=str(ve))
        else:
            raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF compression failed: {str(e)}")
    base_name = os.path.splitext(metadata.original_filename)[0]
    label = "Compressed" if params.mode == "standard" else "Extreme Scan"
    new_filename = f"{base_name}_{label.lower().replace(' ', '_')}{new_ext}"
    target_folder_id = get_derived_folder_id(db, metadata.folder_id)
    
    return VaultService.save_bytes(
        db=db,
        file_bytes=processed_bytes,
        original_filename=new_filename,
        content_type=new_mime,
        title=f"{metadata.title} ({label})",
        is_locked=metadata.is_locked,
        folder_id=target_folder_id
    )

@router.post("/{doc_id}/lock-pdf", response_model=DocumentMetadata)
def lock_pdf(
    doc_id: uuid.UUID,
    params: PdfLockRequest,
    db: Session = Depends(get_db)
):
    raw_bytes, metadata = VaultService.retrieve_document(db=db, doc_id=doc_id)
    if metadata.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Document is not a PDF.")

    try:
        processed_bytes, new_mime, new_ext = DocumentEditorService.lock_pdf(raw_bytes, params.password)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF locking failed: {str(e)}")

    base_name = os.path.splitext(metadata.original_filename)[0]
    new_filename = f"{base_name}_locked{new_ext}"
    target_folder_id = get_derived_folder_id(db, metadata.folder_id)
    
    return VaultService.save_bytes(
        db=db,
        file_bytes=processed_bytes,
        original_filename=new_filename,
        content_type=new_mime,
        title=f"{metadata.title} (Locked)",
        is_locked=True,
        folder_id=target_folder_id
    )

@router.post("/{doc_id}/ocr")
def extract_document_text(
    doc_id: uuid.UUID,
    password: str = None,
    db: Session = Depends(get_db)
):
    """Runs local Tesseract OCR on the document in memory."""
    raw_bytes, metadata = VaultService.retrieve_document(db=db, doc_id=doc_id)
    
    try:
        extracted_text = DocumentEditorService.extract_text(
            raw_bytes=raw_bytes, 
            content_type=metadata.content_type, 
            password=password
        )
        return {"status": "success", "text": extracted_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR failed: {str(e)}")

@router.post("/{doc_id}/watermark", response_model=DocumentMetadata)
def stamp_watermark(
    doc_id: uuid.UUID,
    params: WatermarkRequest,
    db: Session = Depends(get_db)
):
    """Applies a visual security stamp and saves as a new file in Processed & Exported."""
    raw_bytes, metadata = VaultService.retrieve_document(db=db, doc_id=doc_id)
    
    try:
        processed_bytes, new_mime, new_ext = DocumentEditorService.apply_watermark(
            raw_bytes, 
            content_type=metadata.content_type, 
            text=params.text,
            password=params.password
        )
    except ValueError as ve:
        raise HTTPException(status_code=403, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Watermarking failed: {str(e)}")

    base_name = os.path.splitext(metadata.original_filename)[0]
    new_filename = f"{base_name}_KYC_stamped{new_ext}"
    target_folder_id = get_derived_folder_id(db, metadata.folder_id)
    
    return VaultService.save_bytes(
        db=db,
        file_bytes=processed_bytes,
        original_filename=new_filename,
        content_type=new_mime,
        title=f"{metadata.title} (Watermarked)",
        is_locked=metadata.is_locked,
        folder_id=target_folder_id
    )