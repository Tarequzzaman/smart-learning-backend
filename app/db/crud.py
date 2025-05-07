from sqlalchemy.orm import Session
from app.db import models , schemas
from app.services.password_helper import get_password_hash , verify_password
from typing import Optional
from datetime import datetime



def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def get_user_by_id(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_all_users(db: Session):
    return db.query(models.User).order_by(models.User.id.asc()).all()

def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.User(
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        hashed_password=get_password_hash(user.password),
        role="user"
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, user: models.User, user_update: schemas.UserUpdate):
    user.first_name = user_update.first_name
    user.last_name = user_update.last_name
    user.role = user_update.role if user_update.role in ('admin', 'user') else 'user'
    db.commit()
    db.refresh(user)
    return user

def delete_user(db: Session, user: models.User):
    db.delete(user)
    db.commit()
    return {"detail": "User deleted successfully"}

def authenticate_user(db: Session, email: str, password: str) -> Optional[models.User]:
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

def create_topic(db: Session, topic: schemas.TopicCreate, user_id: int):
    new_topic = models.Topic(
        title=topic.title,
        description=topic.description,
        created_by_id=user_id
    )
    db.add(new_topic)
    db.commit()
    db.refresh(new_topic)
    return new_topic

def get_all_topics(db: Session):
    return db.query(models.Topic).order_by(models.Topic.id.asc()).all()


def get_all_courses(db: Session):
    return db.query(models.Course).filter(models.Course.is_detail_created_by_ai == True).all()

def get_topic_by_id(db: Session, topic_id: int):
    return db.query(models.Topic).filter(models.Topic.id == topic_id).first()

def update_topic(db: Session, db_topic: models.Topic, updated: schemas.TopicCreate):
    db_topic.title = updated.title
    db_topic.description = updated.description
    db.commit()
    db.refresh(db_topic)
    return db_topic

def delete_topic(db: Session, topic: models.Topic):
    db.delete(topic)
    db.commit()


def insert_log_in_code(db: Session, code: str, user_id: int, expiry_time) -> None:
    reset_code_entry = models.PasswordResetCode(
            user_id=user_id,
            code=code,
            expiry_time=expiry_time,
            status="pending"
    )
    db.add(reset_code_entry)
    db.commit()


def delete_old_pending_code(db: Session, user_id: int) -> None:
    db.query(models.PasswordResetCode).filter(
        models.PasswordResetCode.user_id == user_id,
          models.PasswordResetCode.status == "pending"
    ).delete()
    db.commit()


def get_pending_code_by_user(db: Session, user_id: int):
    return db.query(models.PasswordResetCode).filter(
        models.PasswordResetCode.user_id == user_id,
        models.PasswordResetCode.status == "pending",
        models.PasswordResetCode.expiry_time > datetime.now()
    ).first()

def accept_reset_code(db: Session, reset_entry: models.PasswordResetCode):
    reset_entry.status = "accepted"
    db.commit()



def reseat_password(db: Session, user: models.User, password: str) -> None:
    hashed_password = get_password_hash(password)
    user.hashed_password = hashed_password
    db.commit()



def create_course(
        db: Session,
        course_title: str,
        course_description: str,
        course_level: str,
        topic_id : int
    ) -> None:

    db_course = models.Course(
        course_title=course_title,
        course_description=course_description,
        course_level=course_level,
        topic_id=topic_id,
    )
    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    return db_course

def mark_course_as_built(db: Session, course_id: int):
    db.query(models.Course).filter(models.Course.id == course_id).update({
        "is_detail_created_by_ai": True
    })
    db.commit()

def mark_topic_published(db: Session, topic_id: int):
    db.query(models.Topic).filter(models.Topic.id == topic_id).update({
        "is_published": True
    })
    db.commit()
