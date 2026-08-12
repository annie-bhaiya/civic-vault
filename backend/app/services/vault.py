import uuid
import os
from pathlib import Path
from fastapi import UploadFile, HTTPException
from sqlmodel import Session, select
from app.core.config import settings
from app.core.security import vault_crypto
from app.models.document import DocumentMetadata
import fitz  # Imported for native lock detection

class VaultService:
    
    @staticmethod
    def retrieve_document(db: Session, doc_id: uuid.UUID) -> tuple[bytes, DocumentMetadata]:
        db_doc = db.get(DocumentMetadata, doc_id)
        if not db_doc:
            raise HTTPException(status_code=404, detail="Document not found.")
            
        file_path = Path(db_doc.encrypted_file_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Encrypted file missing from storage.")
            
        with open(file_path, "rb") as f:
            encrypted_bytes = f.read()
            
        decrypted_bytes = vault_crypto.decrypt_bytes(encrypted_bytes)
        return decrypted_bytes, db_doc

    @staticmethod
    def list_documents(db: Session) -> list[DocumentMetadata]:
        statement = select(DocumentMetadata).order_by(DocumentMetadata.created_at.desc())
        return db.exec(statement).all()

    @staticmethod
    async def save_document(
        db: Session, 
        file: UploadFile, 
        title: str,
        document_type: str,
        folder_id: uuid.UUID
    ) -> DocumentMetadata:
        file_bytes = await file.read()
        
        is_locked = False
        content_type = file.content_type or "application/octet-stream"
        
        if content_type == "application/pdf" or (file.filename and file.filename.lower().endswith(".pdf")):
            try:
                temp_pdf = fitz.open(stream=file_bytes, filetype="pdf")
                if temp_pdf.needs_pass:
                    is_locked = True
                temp_pdf.close()
            except Exception as e:
                print(f"[VAULT] Error checking PDF lock status: {e}")
                
        encrypted_bytes = vault_crypto.encrypt_bytes(file_bytes)
        
        doc_id = uuid.uuid4()
        encrypted_filename = f"{doc_id}.enc"
        dest_path = settings.STORAGE_DIR / encrypted_filename
        
        with open(dest_path, "wb") as f:
            f.write(encrypted_bytes)
            
        db_doc = DocumentMetadata(
            id=doc_id,
            title=title or file.filename,
            original_filename=file.filename,
            content_type=content_type,
            file_size_bytes=len(file_bytes),
            encrypted_file_path=str(dest_path),
            is_locked=is_locked,
            document_type=document_type,
            folder_id=folder_id
        )
        
        db.add(db_doc)
        db.commit()
        db.refresh(db_doc)
        return db_doc

    @staticmethod
    def save_bytes(
        db: Session, 
        file_bytes: bytes, 
        original_filename: str, 
        content_type: str, 
        title: str,
        is_locked: bool = False,
        document_type: str = "Derived/Processed",
        folder_id: uuid.UUID = None
    ) -> DocumentMetadata:
        encrypted_bytes = vault_crypto.encrypt_bytes(file_bytes)
        
        doc_id = uuid.uuid4()
        encrypted_filename = f"{doc_id}.enc"
        dest_path = settings.STORAGE_DIR / encrypted_filename
        
        with open(dest_path, "wb") as f:
            f.write(encrypted_bytes)
            
        db_doc = DocumentMetadata(
            id=doc_id,
            title=title,
            original_filename=original_filename,
            content_type=content_type,
            file_size_bytes=len(file_bytes),
            encrypted_file_path=str(dest_path),
            is_locked=is_locked,
            document_type=document_type,
            folder_id=folder_id
        )
        
        db.add(db_doc)
        db.commit()
        db.refresh(db_doc)
        return db_doc