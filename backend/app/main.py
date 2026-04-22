from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, SessionLocal, engine
from app import models  # noqa: F401
from app.routers import remittances, worklogs
from app.seed_data import load_seed_if_empty


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        load_seed_if_empty(db)
    finally:
        db.close()
    yield


app = FastAPI(title="WorkLog Settlement API", lifespan=lifespan)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(worklogs.router)
app.include_router(remittances.router)


@app.get("/health")
def health():
    return {"status": "ok"}
