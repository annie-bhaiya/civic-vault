import uuid
from typing import List
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, Form, Response, HTTPException
from sqlmodel import Session
from app.db.session import get_db
from app.models.document import DocumentMetadata
from app.services.vault import VaultService
from app.schemas.editor import DocumentRenameRequest

router = APIRouter(prefix="/documents", tags=["Documents"])

@router.post("/upload", response_model=DocumentMetadata)
async def upload_document(
    title: str = Form(...),
    document_type: str = Form(...),
    folder_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    return await VaultService.save_document(
        db=db, 
        file=file, 
        title=title, 
        document_type=document_type, 
        folder_id=folder_id
    )

@router.get("/", response_model=List[DocumentMetadata])
def get_all_documents(db: Session = Depends(get_db)):
    return VaultService.list_documents(db=db)

@router.get("/{doc_id}/download")
def download_document(doc_id: uuid.UUID, pin: str = None, db: Session = Depends(get_db)):
    """Forces a direct file download behind a Share-Gate Export PIN."""
    
    # THE SHARE-GATE SECURITY CHECK
    if pin != "1234":
        raise HTTPException(status_code=403, detail="Access Denied: Invalid Export PIN.")
        
    raw_bytes, metadata = VaultService.retrieve_document(db=db, doc_id=doc_id)
    return Response(
        content=raw_bytes,
        media_type=metadata.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{metadata.original_filename}"'
        }
    )
@router.get("/{doc_id}/preview")
def preview_document(doc_id: uuid.UUID, db: Session = Depends(get_db)):
    """Streams the file inline so the browser can render it in a new tab."""
    raw_bytes, metadata = VaultService.retrieve_document(db=db, doc_id=doc_id)
    return Response(
        content=raw_bytes,
        media_type=metadata.content_type,
        headers={
            "Content-Disposition": f'inline; filename="{metadata.original_filename}"'
        }
    )

@router.delete("/{doc_id}")
def delete_document(doc_id: uuid.UUID, db: Session = Depends(get_db)):
    db_doc = db.get(DocumentMetadata, doc_id)
    if not db_doc:
        raise HTTPException(status_code=404, detail="Document not found.")
        
    file_path = Path(db_doc.encrypted_file_path)
    if file_path.exists():
        file_path.unlink()
        
    db.delete(db_doc)
    db.commit()
    return {"status": "success", "message": "Document permanently deleted."}

@router.patch("/{doc_id}/rename", response_model=DocumentMetadata)
def rename_document(
    doc_id: uuid.UUID, 
    params: DocumentRenameRequest, 
    db: Session = Depends(get_db)
):
    db_doc = db.get(DocumentMetadata, doc_id)
    if not db_doc:
        raise HTTPException(status_code=404, detail="Document not found.")
        
    db_doc.title = params.title
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    return db_doc