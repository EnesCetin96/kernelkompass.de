import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint, Boolean
from sqlalchemy.orm import relationship
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    email_verified = Column(Boolean, default=False, nullable=False)
    verification_token = Column(String(128), nullable=True)
    verification_token_expires = Column(DateTime, nullable=True)

    reset_token = Column(String(128), nullable=True)
    reset_token_expires = Column(DateTime, nullable=True)

    # Kayıt sırasında sorulan açıklama-dili tercihi ("tr" veya "de").
    # İngilizce ana metin her zaman sabit gösterilir; bu sadece altındaki
    # açıklama katmanının hangi dilde görüneceğini belirler.
    preferred_language = Column(String(2), default="tr", nullable=False)

    # Yorum moderasyon sistemi için admin ayrımı. Varsayılan False —
    # ilk admin hesabı deploy sonrası veritabanında manuel olarak
    # işaretlenecek (bkz. deploy notları / migration adımı).
    is_admin = Column(Boolean, default=False, nullable=False)

    data_entries = relationship(
        "UserData", back_populates="owner", cascade="all, delete-orphan"
    )
    comments = relationship(
        "Comment",
        back_populates="author",
        cascade="all, delete-orphan",
        foreign_keys="Comment.user_id",
    )


class UserData(Base):
    """
    Generic key -> value store per user.
    Used for: 'notes', 'terminal_history', 'progress', and any future
    workbook state that needs to sync across devices.
    """

    __tablename__ = "user_data"
    __table_args__ = (UniqueConstraint("user_id", "key", name="uq_user_key"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    key = Column(String(64), nullable=False)
    value = Column(Text, nullable=False, default="")
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    owner = relationship("User", back_populates="data_entries")


class Comment(Base):
    """
    Landing page yorum/moderasyon sistemi. Sadece giriş yapmış
    kullanıcılar yorum bırakabilir; yorum admin onayından geçmeden
    herkese görünmez (status='pending' -> 'approved'/'rejected').
    """

    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)

    # "pending" | "approved" | "rejected"
    status = Column(String(16), default="pending", nullable=False, index=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    # Admin izlenebilirliği: kim, ne zaman onayladı/reddetti.
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    author = relationship("User", back_populates="comments", foreign_keys=[user_id])


class Ad(Base):
    """
    Website (landing page) reklam panoları. Sabit 6 slot vardır
    (left1/left2/left3/right1/right2/right3); her slotta en fazla bir
    aktif görsel bulunur — yeni yükleme eskisinin yerini alır. Sadece
    admin panelinden dosya yükleme ile doldurulur (dış URL desteklenmiyor).
    Uygulama (webapp) tarafında HİÇBİR reklam gösterimi yoktur — bu
    tablo sadece website/ landing page için kullanılır.
    """

    __tablename__ = "ads"

    id = Column(Integer, primary_key=True, index=True)
    slot = Column(String(16), unique=True, nullable=False, index=True)
    image_filename = Column(String(255), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
