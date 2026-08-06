import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from .. import models, schemas, auth
from ..database import get_db

router = APIRouter(prefix="/api/data", tags=["data"])

# Keys the frontend is allowed to sync. Keeping an allow-list avoids
# arbitrary key spam and makes future migrations predictable.
ALLOWED_KEYS = {"notes", "terminal_history", "progress"}

# --- Kota ayarları ---
# Bu proje ücretsiz ve herkese açık olduğu için, tek bir kullanıcının
# aşırı veri biriktirip sunucu depolamasını şişirmesini engellemek için
# makul sınırlar koyuyoruz. Sınırlar UTF-8 byte cinsinden.
KEY_LIMITS_BYTES = {
    "notes": 300 * 1024,             # ~300 KB (uzun notlar için fazlasıyla yeterli)
    "terminal_history": 150 * 1024,  # ~150 KB
    "progress": 20 * 1024,           # küçük bir JSON, pratikte hiç dolmaz
}
TOTAL_LIMIT_BYTES = 500 * 1024  # kullanıcı başına toplam üst sınır (~500 KB)
WARNING_THRESHOLD = 0.8  # %80'e ulaşınca frontend'e uyarı sinyali gönder


def _byte_len(s: str) -> int:
    return len(s.encode("utf-8"))


@router.get("/quota")
def get_quota(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Kullanıcının her anahtar (key) için ve toplamda ne kadar yer kapladığını
    döndürür. Frontend bunu periyodik olarak (örn. her senkronda) kontrol
    edip %80'i geçtiğinde kullanıcıya 'verini indir ve temizle' bildirimi
    gösterebilir.
    """
    entries = (
        db.query(models.UserData)
        .filter(models.UserData.user_id == current_user.id)
        .all()
    )
    usage = {e.key: _byte_len(e.value) for e in entries}
    total_used = sum(usage.values())

    per_key = {}
    for key, limit in KEY_LIMITS_BYTES.items():
        used = usage.get(key, 0)
        per_key[key] = {
            "used_bytes": used,
            "limit_bytes": limit,
            "percent": round(used / limit * 100, 1) if limit else 0,
            "warning": used >= limit * WARNING_THRESHOLD,
        }

    return {
        "per_key": per_key,
        "total": {
            "used_bytes": total_used,
            "limit_bytes": TOTAL_LIMIT_BYTES,
            "percent": round(total_used / TOTAL_LIMIT_BYTES * 100, 1),
            "warning": total_used >= TOTAL_LIMIT_BYTES * WARNING_THRESHOLD,
        },
    }


@router.get("", response_model=List[schemas.DataOut])
def get_all_data(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch everything at once — used right after login to hydrate the app."""
    return (
        db.query(models.UserData)
        .filter(models.UserData.user_id == current_user.id)
        .all()
    )


@router.get("/{key}", response_model=schemas.DataOut)
def get_data(
    key: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    entry = (
        db.query(models.UserData)
        .filter(models.UserData.user_id == current_user.id, models.UserData.key == key)
        .first()
    )
    if not entry:
        # Not an error — just means nothing has been saved for this key yet
        return schemas.DataOut(key=key, value="", updated_at=__import__("datetime").datetime.utcnow())
    return entry


@router.put("/{key}", response_model=schemas.DataOut)
def set_data(
    key: str,
    payload: schemas.DataValue,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    if key not in ALLOWED_KEYS:
        raise HTTPException(status_code=400, detail=f"Geçersiz anahtar: {key}")

    new_size = _byte_len(payload.value)
    key_limit = KEY_LIMITS_BYTES.get(key)
    if key_limit is not None and new_size > key_limit:
        raise HTTPException(
            status_code=413,
            detail=(
                f"'{key}' için izin verilen boyut aşıldı "
                f"({new_size} / {key_limit} byte). Lütfen verini indirip "
                f"bir kısmını temizle."
            ),
        )

    # Toplam kotayı da kontrol et (bu key hariç diğerlerinin toplamı + yeni değer)
    other_entries_total = (
        db.query(func.coalesce(func.sum(func.length(models.UserData.value)), 0))
        .filter(models.UserData.user_id == current_user.id, models.UserData.key != key)
        .scalar()
        or 0
    )
    if other_entries_total + new_size > TOTAL_LIMIT_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(
                "Toplam veri kotan doldu. Lütfen notlarını/terminal geçmişini "
                "indirip cihazına kaydettikten sonra sunucudaki kopyayı temizle."
            ),
        )

    entry = (
        db.query(models.UserData)
        .filter(models.UserData.user_id == current_user.id, models.UserData.key == key)
        .first()
    )
    if entry:
        entry.value = payload.value
    else:
        entry = models.UserData(user_id=current_user.id, key=key, value=payload.value)
        db.add(entry)

    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/{key}")
def clear_data(
    key: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Kullanıcının kendi verisini temizlemesi için (kota uyarısına karşılık gelen aksiyon)."""
    entry = (
        db.query(models.UserData)
        .filter(models.UserData.user_id == current_user.id, models.UserData.key == key)
        .first()
    )
    if entry:
        db.delete(entry)
        db.commit()
    return {"key": key, "cleared": True}
