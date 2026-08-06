import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database import Base, engine
from .routers import auth as auth_router
from .routers import data as data_router
from .routers import comments as comments_router
from .routers import ads as ads_router

# Create tables if they don't exist yet (fine for this project's scale;
# for bigger schemas you'd switch to Alembic migrations)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Linux & DevOps Çalışma Kitabı API")

cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(data_router.router)
app.include_router(comments_router.router)
app.include_router(ads_router.router)

# Reklam görselleri (yüklenen dosyalar) — ads_router.UPLOAD_DIR zaten
# router import edilirken os.makedirs ile oluşturuluyor. nginx /api/
# location'ı buraya proxy ettiği için bu path public olarak erişilebilir.
app.mount("/api/ads/files", StaticFiles(directory=ads_router.UPLOAD_DIR), name="ad-files")


@app.get("/api/health")
def health():
    return {"status": "ok"}
