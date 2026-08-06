import os
import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from .. import models, schemas, auth
from ..database import get_db

router = APIRouter(prefix="/api/ads", tags=["ads"])

# Sabit 6 slot: sol taraf 3, sağ taraf 3. Sırayla üstten alta render edilir.
VALID_SLOTS = {"left1", "left2", "left3", "right1", "right2", "right3"}

# Container içinde kalıcı (docker-compose'da named volume ile bağlı) dizin.
UPLOAD_DIR = "/app/uploads/ads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_CONTENT_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
}
MAX_UPLOAD_BYTES = 3 * 1024 * 1024  # 3 MB


def _image_url(image_filename: str) -> str:
    # nginx /api/ location'ı backend'e proxy ediyor, bu yüzden bu path
    # doğrudan public olarak erişilebilir (main.py'de StaticFiles mount'u).
    return f"/api/ads/files/{image_filename}"


def _to_ad_out(ad: models.Ad) -> schemas.AdOut:
    return schemas.AdOut(slot=ad.slot, image_url=_image_url(ad.image_filename), uploaded_at=ad.uploaded_at)


@router.get("", response_model=List[schemas.AdOut])
def list_active_ads(db: Session = Depends(get_db)):
    """Herkese açık — landing page hangi slotların dolu olduğunu ve
    görsel URL'lerini buradan öğrenir. Boş slotlar listede hiç yer almaz."""
    ads = db.query(models.Ad).all()
    return [_to_ad_out(a) for a in ads]


@router.post("/{slot}", response_model=schemas.AdOut)
async def upload_ad(
    slot: str,
    file: UploadFile = File(...),
    current_admin: models.User = Depends(auth.get_current_admin),
    db: Session = Depends(get_db),
):
    """Admin, belirli bir slota görsel yükler. Slotta zaten bir görsel
    varsa eskisi silinir ve yenisiyle değiştirilir (upsert)."""
    if slot not in VALID_SLOTS:
        raise HTTPException(status_code=400, detail=f"Geçersiz slot: {slot}")

    ext = ALLOWED_CONTENT_TYPES.get(file.content_type)
    if not ext:
        raise HTTPException(
            status_code=400,
            detail="Sadece PNG, JPEG veya WEBP görsel yüklenebilir",
        )

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="Görsel 3 MB'tan büyük olamaz")

    existing = db.query(models.Ad).filter(models.Ad.slot == slot).first()
    if existing:
        old_path = os.path.join(UPLOAD_DIR, existing.image_filename)
        if os.path.exists(old_path):
            os.remove(old_path)

    filename = f"{slot}{ext}"
    with open(os.path.join(UPLOAD_DIR, filename), "wb") as f:
        f.write(contents)

    if existing:
        existing.image_filename = filename
        existing.uploaded_at = datetime.datetime.utcnow()
        ad = existing
    else:
        ad = models.Ad(slot=slot, image_filename=filename)
        db.add(ad)

    db.commit()
    db.refresh(ad)
    return _to_ad_out(ad)


@router.delete("/{slot}")
def delete_ad(
    slot: str,
    current_admin: models.User = Depends(auth.get_current_admin),
    db: Session = Depends(get_db),
):
    if slot not in VALID_SLOTS:
        raise HTTPException(status_code=400, detail=f"Geçersiz slot: {slot}")

    ad = db.query(models.Ad).filter(models.Ad.slot == slot).first()
    if not ad:
        raise HTTPException(status_code=404, detail="Bu slotta görsel yok")

    path = os.path.join(UPLOAD_DIR, ad.image_filename)
    if os.path.exists(path):
        os.remove(path)

    db.delete(ad)
    db.commit()
    return {"deleted": True, "slot": slot}
