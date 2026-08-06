import datetime
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    # Kayıt ekranında sorulan açıklama dili tercihi. Varsayılan "tr" —
    # eski/az bilgili istemciler bu alanı hiç göndermezse de kayıt bozulmaz.
    preferred_language: str = Field(default="tr", pattern="^(tr|de)$")


class UserLogin(BaseModel):
    # Kullanıcı adı VEYA e-posta ile giriş yapılabilir — hangisini
    # yazdığını backend otomatik anlıyor (bkz. routers/auth.py).
    identifier: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    email_verified: bool
    preferred_language: str
    is_admin: bool

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class MessageOut(BaseModel):
    message: str


class VerifyEmailRequest(BaseModel):
    token: str


class ForgotPasswordRequest(BaseModel):
    # Kullanıcı adı VEYA e-posta kabul edilir (login ile tutarlı olsun diye).
    identifier: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=6, max_length=128)


class SetLanguageRequest(BaseModel):
    preferred_language: str = Field(pattern="^(tr|de)$")


class DataValue(BaseModel):
    value: str


class DataOut(BaseModel):
    key: str
    value: str
    updated_at: datetime.datetime

    class Config:
        from_attributes = True


# --- Yorum / moderasyon sistemi ---

class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class CommentOut(BaseModel):
    id: int
    content: str
    status: str
    created_at: datetime.datetime
    author_username: str

    class Config:
        from_attributes = True


class CommentModerateRequest(BaseModel):
    # approve/reject endpoint'lerinde body gerekmiyor ama ileride
    # (örn. red gerekçesi eklemek için) genişletilebilsin diye
    # placeholder olarak tutuluyor.
    pass


# --- Reklam panoları (sadece website/ landing page) ---

class AdOut(BaseModel):
    slot: str
    image_url: str
    uploaded_at: datetime.datetime

    class Config:
        from_attributes = True
