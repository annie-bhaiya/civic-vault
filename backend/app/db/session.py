from sqlmodel import SQLModel, create_engine, Session
from app.core.config import settings

db_path = settings.BASE_DIR / settings.DB_NAME
sqlite_url = f"sqlite:///{db_path}"

engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})

def init_db():
    SQLModel.metadata.create_all(engine)

def get_db():
    with Session(engine) as session:
        yield session