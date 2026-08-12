import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.db.session import get_db
from app.models.document import DocumentMetadata
from app.schemas.audit import AuditReport, DocMetadataUpdate
from app.services.audit import AuditService

router = APIRouter(prefix="/audit", tags=["Audit & Intelligence"])

@router.get("/report", response_model=AuditReport)
def get_audit_report(db: Session = Depends(get_db)):
    documents = db.exec(select(DocumentMetadata)).all()
    return AuditService.generate_report(documents)

@router.patch("/documents/{doc_id}")
def update_document_intelligence(
    doc_id: uuid.UUID,
    params: DocMetadataUpdate,
    db: Session = Depends(get_db)
):
    doc = db.get(DocumentMetadata, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
        
    doc.extracted_name = params.extracted_name
    doc.extracted_dob = params.extracted_dob
    doc.biometric_update_date = params.biometric_update_date
    
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return {"status": "success", "message": "Intelligence data saved."}