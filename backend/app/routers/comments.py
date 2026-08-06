import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, auth
from ..database import get_db

router = APIRouter(prefix="/api/comments", tags=["comments"])


def _to_comment_out(comment: models.Comment) -> schemas.CommentOut:
    """Comment ORM objesini CommentOut'a çevirir. author_username modelde
    bir kolon değil (User üzerinden geliyor), bu yüzden elle set ediyoruz."""
    return schemas.CommentOut(
        id=comment.id,
        content=comment.content,
        status=comment.status,
        created_at=comment.created_at,
        author_username=comment.author.username,
    )


@router.post("", response_model=schemas.CommentOut, status_code=201)
def create_comment(
    payload: schemas.CommentCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Giriş yapmış herhangi bir kullanıcı yorum gönderebilir. Yorum
    'pending' durumunda kaydedilir, admin onaylayana kadar herkese
    görünmez."""
    comment = models.Comment(
        user_id=current_user.id,
        content=payload.content,
        status="pending",
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return _to_comment_out(comment)


@router.get("", response_model=List[schemas.CommentOut])
def list_approved_comments(db: Session = Depends(get_db)):
    """Herkese açık — girişsiz kullanıcılar dahil (landing page için).
    Sadece 'approved' durumundaki yorumları döndürür, en yeniden eskiye."""
    comments = (
        db.query(models.Comment)
        .filter(models.Comment.status == "approved")
        .order_by(models.Comment.created_at.desc())
        .all()
    )
    return [_to_comment_out(c) for c in comments]


@router.get("/pending", response_model=List[schemas.CommentOut])
def list_pending_comments(
    current_admin: models.User = Depends(auth.get_current_admin),
    db: Session = Depends(get_db),
):
    """Sadece admin. Onay bekleyen yorumları en eskiden yeniye sıralar
    (kuyruk mantığı — ilk gelen ilk onaylansın)."""
    comments = (
        db.query(models.Comment)
        .filter(models.Comment.status == "pending")
        .order_by(models.Comment.created_at.asc())
        .all()
    )
    return [_to_comment_out(c) for c in comments]


@router.get("/all", response_model=List[schemas.CommentOut])
def list_all_comments(
    current_admin: models.User = Depends(auth.get_current_admin),
    db: Session = Depends(get_db),
):
    """Sadece admin. Durumu ne olursa olsun (pending/approved/rejected)
    TÜM yorumları en yeniden eskiye döner — admin panelindeki tek liste
    görünümü (silme dahil yönetim) bunu kullanır."""
    comments = (
        db.query(models.Comment)
        .order_by(models.Comment.created_at.desc())
        .all()
    )
    return [_to_comment_out(c) for c in comments]


def _moderate(
    comment_id: int,
    new_status: str,
    current_admin: models.User,
    db: Session,
) -> schemas.CommentOut:
    comment = db.query(models.Comment).filter(models.Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Yorum bulunamadı")
    if comment.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Bu yorum zaten '{comment.status}' durumunda, tekrar işlenemez",
        )

    comment.status = new_status
    comment.reviewed_at = datetime.datetime.utcnow()
    comment.reviewed_by = current_admin.id
    db.commit()
    db.refresh(comment)
    return _to_comment_out(comment)


@router.post("/{comment_id}/approve", response_model=schemas.CommentOut)
def approve_comment(
    comment_id: int,
    current_admin: models.User = Depends(auth.get_current_admin),
    db: Session = Depends(get_db),
):
    return _moderate(comment_id, "approved", current_admin, db)


@router.post("/{comment_id}/reject", response_model=schemas.CommentOut)
def reject_comment(
    comment_id: int,
    current_admin: models.User = Depends(auth.get_current_admin),
    db: Session = Depends(get_db),
):
    return _moderate(comment_id, "rejected", current_admin, db)


@router.delete("/{comment_id}")
def delete_comment(
    comment_id: int,
    current_admin: models.User = Depends(auth.get_current_admin),
    db: Session = Depends(get_db),
):
    """Sadece admin. Durumu ne olursa olsun (pending/approved/rejected)
    bir yorumu kalıcı olarak siler."""
    comment = db.query(models.Comment).filter(models.Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Yorum bulunamadı")
    db.delete(comment)
    db.commit()
    return {"deleted": True, "id": comment_id}
