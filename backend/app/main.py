from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from app.core.config import settings
from app.db.session import init_db, engine
from app.models.document import Folder
from app.api.documents import router as document_router
from app.api.editor import router as editor_router
from app.api.folders import router as folder_router
from app.api.audit import router as audit_router

def seed_default_folders():
    """Automatically generates generic system folders for any user."""
    with Session(engine) as db:
        default_folders = [
            ("Vault Source (Immutable)", True),
            ("Processed & Exported", False),
            ("Identity & KYC", False)
        ]
        for name, is_immutable in default_folders:
            folder = db.exec(select(Folder).where(Folder.name == name)).first()
            if not folder:
                db.add(Folder(name=name, is_immutable=is_immutable))
        db.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_default_folders()
    print("[INIT] Database initialized, folders seeded, and local vault ready.")
    yield

app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(document_router)
app.include_router(editor_router)
app.include_router(folder_router)
app.include_router(audit_router)

@app.get("/")
def health_check():
    return {"status": "online", "vault": "locked & encrypted"}