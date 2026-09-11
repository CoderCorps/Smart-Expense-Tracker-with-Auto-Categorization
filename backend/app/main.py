from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.v1.router import api_router
from backend.app.core.config import settings
from backend.app.db.database import Base, SessionLocal, engine
from backend.app.models.category import DEFAULT_CATEGORIES, Category


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    _seed_default_categories()
    yield


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


def _seed_default_categories():
    db = SessionLocal()
    try:
        existing = {c.name: c for c in db.query(Category).all()}
        for name, description in DEFAULT_CATEGORIES.items():
            category = existing.get(name)
            if category is None:
                db.add(Category(name=name, description=description, is_default=True))
            elif category.description is None:
                # Backfill descriptions for DBs seeded before they existed.
                category.description = description
        db.commit()
    finally:
        db.close()


@app.get("/")
def root():
    return {"status": "ok", "message": f"{settings.PROJECT_NAME} is running"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)