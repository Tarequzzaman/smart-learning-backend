import enum
from datetime import datetime
from operator import index

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship

from app.db.database import Base


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

    topics = relationship(
        "Topic", back_populates="creator", cascade="all, delete-orphan"
    )
    topic_preferences = relationship(
        "UserTopicPreference", back_populates="user", cascade="all, delete-orphan"
    )

    course_interactions = relationship(  # ✅ FIXED name
        "CourseInteraction",
        back_populates="user",  # ✅ Matches CourseInteraction.user
        cascade="all, delete-orphan",
    )


class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String)
    created_by_id = Column(Integer, ForeignKey("users.id"))
    is_published = Column(Boolean, default=False)

    creator = relationship("User", back_populates="topics")
    courses = relationship(
        "Course", back_populates="topic", cascade="all, delete-orphan"
    )
    user_preferences = relationship(
        "UserTopicPreference", back_populates="topic", cascade="all, delete-orphan"
    )


class UserTopicPreference(Base):
    __tablename__ = "user_topic_preference"  # Correct table name

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="topic_preferences")
    topic = relationship("Topic", back_populates="user_preferences")


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    course_title = Column(String, nullable=False)
    course_description = Column(String, nullable=False)
    course_level = Column(String, nullable=False)
    is_published = Column(Boolean, default=False)
    is_detail_created_by_ai = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    topic = relationship("Topic", back_populates="courses")

    user_interactions = relationship(
        "CourseInteraction",
        back_populates="course",
        cascade="all, delete-orphan",  # ✅ this line is essential
    )
    __table_args__ = (Index("index_course_topic", "topic_id"),)


class PasswordResetCode(Base):
    __tablename__ = "password_reset_codes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 👈 foreign key
    code = Column(String(6), nullable=False)
    expiry_time = Column(DateTime, nullable=False)
    status = Column(String(20), nullable=False, default="pending")

    user = relationship("User")  # Optional, for easy joining later


class PendingVerificationCode(Base):
    __tablename__ = "pending_verification_codes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(6), nullable=False)
    email = Column(String, nullable=False)
    expiry_time = Column(DateTime, nullable=False)
    accepted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class CourseInteraction(Base):
    __tablename__ = "course_interactions"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    course_id = Column(
        Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )

    course_progress = Column(Integer, default=0)

    user = relationship(
        "User",
        back_populates="course_interactions",  # ✅ This now matches
        passive_deletes=True,
    )

    course = relationship(
        "Course",
        back_populates="user_interactions",
        passive_deletes=True,  # ✅ Important here as well
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "course_id", name="uix_user_course"),
        Index("index_user_course", "user_id", "course_id"),
        index("user_id_index", "user_id"),
    )


class CourseSectionQuizProgress(Base):
    __tablename__ = "course_section_quiz_progress"

    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    course_id = Column(
        Integer, ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True
    )
    section_index = Column(Integer, primary_key=True)
    passed = Column(Boolean, default=False, nullable=False)
    passed_at = Column(DateTime(timezone=True))


class SectionQuiz(Base):
    __tablename__ = "section_quizzes"

    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"))
    section_index = Column(Integer, nullable=False)
    data = Column(JSON, nullable=False)
