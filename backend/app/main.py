from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.v1.router import api_router
from backend.app.core.config import settings
from backend.app.db.database import Base, SessionLocal, engine
from backend.app.models.category import DEFAULT_CATEGORIES, Category

app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.on_event("startup")
def on_startup():
    # For a project this size, create_all() is enough — no migration tool
    # needed. If this were going to production long-term you'd reach for
    # Alembic, but that's overkill for a 1-month internship project.
    Base.metadata.create_all(bind=engine)
    _seed_default_categories()


def _seed_default_categories():
    db = SessionLocal()
    try:
        existing = {c.name for c in db.query(Category).all()}
        for name in DEFAULT_CATEGORIES:
            if name not in existing:
                db.add(Category(name=name, is_default=True))
        db.commit()
    finally:
        db.close()


@app.get("/")
def root():
    return {"status": "ok", "message": f"{settings.PROJECT_NAME} is running"}

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)