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
    courses = relationship("Course", back_populates="topic", cascade="all, delete-orphan")


class UserTopicPreference(Base):
    __tablename__ = "user_topic_preference"  # Correct table name

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="topic_preferences")
    topic = relationship("Topic", back_populates="user_preferences")


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    course_title = Column(String, nullable=False)
    course_description = Column(String, nullable=False)
    course_level = Column(String, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    topic = relationship("Topic", back_populates="courses")



class PasswordResetCode(Base):
    __tablename__ = "password_reset_codes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 👈 foreign key
    code = Column(String(6), nullable=False)
    expiry_time = Column(DateTime, nullable=False)
    status = Column(String(20), nullable=False, default="pending")

    user = relationship("User")  # Optional, for easy joining later