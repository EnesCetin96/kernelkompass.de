import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from .. import models, schemas, auth
from ..database import get_db
from ..email_utils import send_verification_email, send_password_reset_email

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _find_user_by_identifier(db: Session, identifier: str):
    """Kullanıcı adı VEYA e-posta ile arama (login ve şifremi-unuttum ortak kullanır)."""
    return (
        db.query(models.User)
        .filter(or_(models.User.username == identifier, models.User.email == identifier))
        .first()
    )


@router.post("/register", response_model=schemas.Token, status_code=status.HTTP_201_CREATED)
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    existing_username = db.query(models.User).filter(models.User.username == payload.username).first()
    if existing_username:
        raise HTTPException(status_code=400, detail="Bu kullanıcı adı zaten alınmış")

    existing_email = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Bu e-posta adresiyle zaten bir hesap var")

    verification_token = auth.generate_token()
    user = models.User(
        username=payload.username,
        email=payload.email,
        password_hash=auth.hash_password(payload.password),
        email_verified=False,
        verification_token=verification_token,
        verification_token_expires=datetime.datetime.utcnow()
        + datetime.timedelta(hours=auth.VERIFICATION_TOKEN_EXPIRE_HOURS),
        preferred_language=payload.preferred_language,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    send_verification_email(user.email, user.username, verification_token)

    # Karar: doğrulama olmadan da giriş yapılabilsin (kullanıcı isteği) —
    # bu yüzden kayıt anında token veriyoruz, frontend "e-postanı doğrula"
    # hatırlatmasını email_verified=False olduğu için ayrıca gösterecek.
    token = auth.create_access_token({"sub": str(user.id)})
    return schemas.Token(access_token=token, user=user)


@router.post("/login", response_model=schemas.Token)
def login(payload: schemas.UserLogin, db: Session = Depends(get_db)):
    user = _find_user_by_identifier(db, payload.identifier)
    if not user or not auth.verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Kullanıcı adı/e-posta veya şifre hatalı")

    token = auth.create_access_token({"sub": str(user.id)})
    return schemas.Token(access_token=token, user=user)


@router.get("/me", response_model=schemas.UserOut)
def me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user


@router.put("/language", response_model=schemas.UserOut)
def set_language(
    payload: schemas.SetLanguageRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Hesap panelinden (sec-account) açıklama dilini sonradan değiştirmek için."""
    current_user.preferred_language = payload.preferred_language
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/verify-email", response_model=schemas.MessageOut)
def verify_email(payload: schemas.VerifyEmailRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.verification_token == payload.token).first()
    if not user or not user.verification_token_expires or user.verification_token_expires < datetime.datetime.utcnow():
        raise HTTPException(status_code=400, detail="Doğrulama bağlantısının süresi dolmuş veya geçersiz")

    user.email_verified = True
    user.verification_token = None
    user.verification_token_expires = None
    db.commit()
    return schemas.MessageOut(message="E-postan doğrulandı, artık giriş yapabilirsin.")


@router.post("/resend-verification", response_model=schemas.MessageOut)
def resend_verification(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Kullanıcı zaten giriş yapmış durumda (doğrulanmamış olsa da giriş
    yapılabiliyor) — bu yüzden bu endpoint auth gerektiriyor, tekrar
    e-posta yazmasına gerek yok."""
    if current_user.email_verified:
        return schemas.MessageOut(message="E-postan zaten doğrulanmış.")

    token = auth.generate_token()
    current_user.verification_token = token
    current_user.verification_token_expires = datetime.datetime.utcnow() + datetime.timedelta(
        hours=auth.VERIFICATION_TOKEN_EXPIRE_HOURS
    )
    db.commit()
    send_verification_email(current_user.email, current_user.username, token)
    return schemas.MessageOut(message="Doğrulama e-postası tekrar gönderildi.")


@router.post("/forgot-password", response_model=schemas.MessageOut)
def forgot_password(payload: schemas.ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = _find_user_by_identifier(db, payload.identifier)
    # Güvenlik: hesap olsun ya da olmasın AYNI mesaj dönülür — aksi halde
    # bu endpoint "bu kullanıcı adı/e-posta kayıtlı mı" öğrenmek için
    # kötüye kullanılabilir (account enumeration).
    generic_msg = schemas.MessageOut(
        message="Eğer bu kullanıcı adı/e-posta ile bir hesap varsa, şifre sıfırlama bağlantısı gönderildi."
    )
    if not user:
        return generic_msg

    token = auth.generate_token()
    user.reset_token = token
    user.reset_token_expires = datetime.datetime.utcnow() + datetime.timedelta(
        hours=auth.RESET_TOKEN_EXPIRE_HOURS
    )
    db.commit()
    send_password_reset_email(user.email, user.username, token)
    return generic_msg


@router.post("/reset-password", response_model=schemas.MessageOut)
def reset_password(payload: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.reset_token == payload.token).first()
    if not user or not user.reset_token_expires or user.reset_token_expires < datetime.datetime.utcnow():
        raise HTTPException(status_code=400, detail="Şifre sıfırlama bağlantısının süresi dolmuş veya geçersiz")

    user.password_hash = auth.hash_password(payload.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    # Bonus: şifre sıfırlama e-postasındaki bağlantıya tıklayabildiyse,
    # bu e-postaya gerçekten erişimi olduğu kanıtlanmış olur.
    user.email_verified = True
    db.commit()
    return schemas.MessageOut(message="Şifren değiştirildi, artık yeni şifrenle giriş yapabilirsin.")
