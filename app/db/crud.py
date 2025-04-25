from sqlalchemy.orm import Session
from app.db import models , schemas
from app.services.password_helper import get_password_hash , verify_password
from typing import Optional


def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()


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



