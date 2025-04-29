from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Enum, func, DateTime
from sqlalchemy.orm import relationship
from app.db.database import Base
import enum
from datetime import datetime

class UserRole(str, enum.Enum):
    admin = "admin"
    user = "user"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.user)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    topics = relationship("Topic", back_populates="creator", cascade="all, delete-orphan")



class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String)
    created_by_id = Column(Integer, ForeignKey("users.id"))

    creator = relationship("User", back_populates="topics")


class PasswordResetCode(Base):
    __tablename__ = "password_reset_codes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 👈 foreign key
    code = Column(String(6), nullable=False)
    expiry_time = Column(DateTime, nullable=False)
    status = Column(String(20), nullable=False, default="pending")

    user = relationship("User")  # Optional, for easy joining later