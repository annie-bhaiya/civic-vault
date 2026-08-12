import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.db.session import get_db
from app.models.document import Folder, DocumentMetadata
from app.schemas.editor import FolderCreateRequest, FolderRenameRequest

router = APIRouter(prefix="/folders", tags=["Folders"])

@router.get("/", response_model=List[Folder])
def get_all_folders(db: Session = Depends(get_db)):
    statement = select(Folder).order_by(Folder.created_at.asc())
    return db.exec(statement).all()

@router.post("/", response_model=Folder)
def create_folder(params: FolderCreateRequest, db: Session = Depends(get_db)):
    existing = db.exec(select(Folder).where(Folder.name == params.name)).first()
    if existing:
        raise HTTPException(status_code=400, detail="A folder with this name already exists.")
        
    new_folder = Folder(name=params.name, is_immutable=False)
    db.add(new_folder)
    db.commit()
    db.refresh(new_folder)
    return new_folder

@router.patch("/{folder_id}/rename", response_model=Folder)
def rename_folder(folder_id: uuid.UUID, params: FolderRenameRequest, db: Session = Depends(get_db)):
    folder = db.get(Folder, folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found.")
    if folder.is_immutable:
        raise HTTPException(status_code=403, detail="Cannot rename an immutable system folder.")
        
    folder.name = params.name
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return folder

@router.delete("/{folder_id}")
def delete_folder(folder_id: uuid.UUID, db: Session = Depends(get_db)):
    folder = db.get(Folder, folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found.")
    if folder.is_immutable:
        raise HTTPException(status_code=403, detail="Cannot delete an immutable system folder.")
        
    # Safety Check: Prevent deletion if folder has documents
    docs_in_folder = db.exec(select(DocumentMetadata).where(DocumentMetadata.folder_id == folder_id)).first()
    if docs_in_folder:
        raise HTTPException(status_code=400, detail="Folder is not empty. Move or delete documents first.")
        
    db.delete(folder)
    db.commit()
    return {"status": "success", "message": "Folder deleted."}