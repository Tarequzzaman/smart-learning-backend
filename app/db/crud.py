from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import cast, func
from sqlalchemy.sql.sqltypes import DATE

from app.db import models, schemas
from app.services.password_helper import get_password_hash, verify_password


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
        role="user",
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(db: Session, user: models.User, user_update: schemas.UserUpdate):
    user.first_name = user_update.first_name
    user.last_name = user_update.last_name
    user.role = user_update.role if user_update.role in ("admin", "user") else "user"
    db.commit()
    db.refresh(user)
    return user


def update_user_details(
    db: Session, user: models.User, user_update: schemas.UserUpdateDetails
):
    # Update only first_name and last_name fields
    user.first_name = user_update.first_name
    user.last_name = user_update.last_name

    print(
        f"Updating {user.id} with first_name={user.first_name} and last_name={user.last_name}"
    )

    db.commit()
    db.refresh(user)
    return user


def get_user_selected_topics(db: Session, user_id: int):
    return (
        db.query(models.Topic)
        .join(models.UserTopicPreference)
        .filter(models.UserTopicPreference.user_id == user_id)
        .all()
    )


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
        title=topic.title, description=topic.description, created_by_id=user_id
    )
    db.add(new_topic)
    db.commit()
    db.refresh(new_topic)
    return new_topic

@lru_cache(maxsize=128, typed=False)
def get_all_topics(db: Session):
    return db.query(models.Topic).order_by(models.Topic.id.desc()).all()

@lru_cache(maxsize=128, typed=False)
def get_all_courses(db: Session):
    return (
        db.query(models.Course)
        .filter(models.Course.is_detail_created_by_ai == True)
        .all()
    )

@lru_cache(maxsize=128, typed=False)
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


def insert_log_in_code_forgot_password(
    db: Session, code: str, user_id: int, expiry_time
) -> None:
    reset_code_entry = models.PasswordResetCode(
        user_id=user_id, code=code, expiry_time=expiry_time, status="pending"
    )
    db.add(reset_code_entry)
    db.commit()


def delete_old_pending_code(db: Session, user_id: int) -> None:
    db.query(models.PasswordResetCode).filter(
        models.PasswordResetCode.user_id == user_id,
        models.PasswordResetCode.status == "pending",
    ).delete()
    db.commit()


def get_pending_code_by_user(db: Session, user_id: int):
    return (
        db.query(models.PasswordResetCode)
        .filter(
            models.PasswordResetCode.user_id == user_id,
            models.PasswordResetCode.status == "pending",
            models.PasswordResetCode.expiry_time > datetime.now(),
        )
        .first()
    )


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
    topic_id: int,
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


def get_user_interests(db: Session, user_id: int):
    return (
        db.query(models.Topic)
        .join(models.UserTopicPreference)
        .filter(models.UserTopicPreference.user_id == user_id)
        .all()
    )


def add_user_topic_preferences(db: Session, user_id: int, topic_ids: list):
    preferences = []
    for topic_id in topic_ids:
        existing_preference = (
            db.query(models.UserTopicPreference)
            .filter(
                models.UserTopicPreference.user_id == user_id,
                models.UserTopicPreference.topic_id == topic_id,
            )
            .first()
        )

        if not existing_preference:
            user_topic_preference = models.UserTopicPreference(
                user_id=user_id, topic_id=topic_id
            )
            db.add(user_topic_preference)
            preferences.append(user_topic_preference)

    db.commit()

    for preference in preferences:
        db.refresh(preference)
    return preferences


def mark_course_as_built(db: Session, course_id: int):
    db.query(models.Course).filter(models.Course.id == course_id).update(
        {"is_detail_created_by_ai": True}
    )
    db.commit()


def mark_topic_published(db: Session, topic_id: int):
    db.query(models.Topic).filter(models.Topic.id == topic_id).update(
        {"is_published": True}
    )
    db.commit()


def get_enrolled_courses(db: Session, user_id: int) -> list[tuple]:
    """
    Returns a list of (Course, CourseInteraction) tuples for the user,
    ordered by CourseInteraction.updated_at ascending.
    """
    enrolled_courses = (
        db.query(models.Course, models.CourseInteraction)
        .join(
            models.CourseInteraction,
            models.Course.id == models.CourseInteraction.course_id,
        )
        .filter(models.CourseInteraction.user_id == user_id)
        .filter(models.CourseInteraction.course_progress < 100)
        .order_by(models.CourseInteraction.updated_at.desc())
        .all()
    )
    return enrolled_courses


def get_user_interested_topics(db: Session, user_id: int) -> list:
    """
    Fetch a distinct list of topic IDs that the user has shown interest in.
    """
    result = (
        db.query(models.UserTopicPreference.topic_id)
        .filter(models.UserTopicPreference.user_id == user_id)
        .distinct()
        .all()
    )
    return [row[0] for row in result]


def get_topic_ids_from_enrolled_courses(db: Session, user_id: int) -> list:
    """
    Returns a list of topic IDs based on the user's enrolled courses.
    """
    topic_ids = (
        db.query(models.Course.topic_id)
        .select_from(models.CourseInteraction)
        .join(models.Course, models.CourseInteraction.course_id == models.Course.id)
        .filter(models.CourseInteraction.user_id == user_id)
        .distinct()  # optional: to avoid duplicates
        .all()
    )
    return [topic_id for (topic_id,) in topic_ids]


def get_random_courses(db: Session, limit: int = 10):
    """
    Fetch a random list of published courses from the database.
    """
    # Get total count of available courses
    total_courses = (
        db.query(models.Course)
        .filter(models.Course.is_detail_created_by_ai == True)
        .count()
    )

    if total_courses == 0:
        return []

    # If fewer courses than the limit, return all
    if total_courses <= limit:
        return (
            db.query(models.Course)
            .filter(models.Course.is_detail_created_by_ai == True)
            .all()
        )

    # Get random offset indices (option 1 - efficient for small datasets)
    random_courses = (
        db.query(models.Course)
        .filter(models.Course.is_detail_created_by_ai == True)
        .order_by(func.random())
        .limit(limit)
        .all()
    )

    return random_courses


def get_courses_by_topics(
    db: Session,
    topic_ids: list,
    exclude_course_ids: list,
    limit: int = 10,
) -> list:
    query = db.query(models.Course).filter(
        models.Course.topic_id.in_(topic_ids),
        models.Course.is_detail_created_by_ai == True,
    )
    if exclude_course_ids:
        query = query.filter(~models.Course.id.in_(exclude_course_ids))
    return query.order_by(func.random()).limit(limit).all()


def create_course_interaction(db: Session, user_id: int, course_id: int):
    existing = (
        db.query(models.CourseInteraction)
        .filter_by(user_id=user_id, course_id=course_id)
        .first()
    )

    if not existing:
        new_interaction = models.CourseInteraction(
            user_id=user_id,
            course_id=course_id,
            course_progress=0,  # starts at 0%
        )
        db.add(new_interaction)
        db.commit()
        db.refresh(new_interaction)
        return new_interaction


def get_course_interaction(db: Session, course_id: int, user_id: int) -> dict:
    interaction = (
        db.query(models.CourseInteraction)
        .filter_by(course_id=course_id, user_id=user_id)
        .first()
    )

    if not interaction:
        return {
            "user_id": user_id,
            "course_id": course_id,
            "course_progress": 0,
            "message": "No interaction found.",
        }

    return {
        "user_id": interaction.user_id,
        "course_id": interaction.course_id,
        "course_progress": interaction.course_progress,
        "created_at": interaction.created_at,
        "updated_at": interaction.updated_at,
    }


def update_course_progress(
    db: Session, user_id: int, course_id: int, new_progress: int
):
    interaction = (
        db.query(models.CourseInteraction)
        .filter_by(user_id=user_id, course_id=course_id)
        .first()
    )

    if interaction:
        if new_progress > interaction.course_progress:
            interaction.course_progress = new_progress
            db.commit()
            db.refresh(interaction)
    else:
        # Create a new record
        interaction = models.CourseInteraction(
            user_id=user_id, course_id=course_id, course_progress=new_progress
        )
        db.add(interaction)
        try:
            db.commit()
            db.refresh(interaction)
        except IntegrityError:
            db.rollback()

    return interaction


def get_passed_quiz_section(db: Session, user_id: int, course_id: int):
    return (
        db.query(models.CourseSectionQuizProgress.section_index)
        .filter_by(user_id=user_id, course_id=course_id, passed=True)
        .all()
    )


def insert_quiz_question(
    db, course_id, section_index, question, options, correct_answer, hint=None
):
    record = models.SectionQuiz(
        course_id=course_id,
        section_index=section_index,
        data={
            "question": question,
            "options": options,
            "correctAnswer": correct_answer,
            "hint": hint,
        },
    )
    db.add(record)
    db.commit()


def get_quizes(db: Session, course_id: int, section_index: int):
    course = db.query(models.Course).filter_by(id=course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return (
        db.query(models.SectionQuiz)
        .filter_by(course_id=course_id, section_index=section_index)
        .all()
    )

@lru_cache(maxsize=256, typed=False)
def get_course_by_id(db: Session, course_id: int):
    return db.query(models.Course).filter(models.Course.id == course_id).first()

@lru_cache(maxsize=256, typed=False)
def section_quiz_exists(db: Session, course_id: int, section_index: int) -> bool:
    return (
        db.query(models.SectionQuiz)
        .filter_by(course_id=course_id, section_index=section_index)
        .first()
    )


def mark_quiz_passed(db: Session, user_id: int, course_id: int, section_index: int):
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    course = get_course_by_id(db, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    section_quiz = section_quiz_exists(db, course_id, section_index)

    if not section_quiz:
        raise HTTPException(status_code=404, detail="Section quiz not found")

    record = (
        db.query(models.CourseSectionQuizProgress)
        .filter_by(user_id=user_id, course_id=course_id, section_index=section_index)
        .first()
    )
    if record:
        if not record.passed:  # idempotent
            record.passed = True
            record.passed_at = datetime.now()
    else:
        record = models.CourseSectionQuizProgress(
            user_id=user_id,
            course_id=course_id,
            section_index=section_index,
            passed=True,
            passed_at=datetime.now(),
        )
        db.add(record)
        db.commit()
    return record


def insert_log_in_code(
    db: Session, code: str, user_id: int, expiry_time: datetime, email: str = None
):
    new_entry = models.PendingVerificationCode(
        code=code,
        expiry_time=expiry_time,
        email=email,  # Store email temporarily for new users
    )
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    return new_entry


def get_pending_code_by_email(db: Session, email: str):
    return (
        db.query(models.PendingVerificationCode)
        .filter(models.PendingVerificationCode.email == email)
        .filter(models.PendingVerificationCode.accepted == False)
        .order_by(models.PendingVerificationCode.created_at.desc())
        .first()
    )


def accept_reset_code(db: Session, reset_entry: models.PendingVerificationCode):
    reset_entry.accepted = True
    db.commit()
    db.refresh(reset_entry)
    return reset_entry


def get_completed_courses(db: Session, user_id: int):
    return (
        db.query(models.Course)
        .join(models.CourseInteraction)
        .filter(
            models.CourseInteraction.user_id == user_id,
            models.CourseInteraction.course_progress == 100,
        )
        .all()
    )


# =================================================================
# Admin Analytics


def get_users_count(db: Session) -> int:
    return db.query(models.User).count()


def get_topics_count(db: Session) -> int:
    return db.query(models.Topic).count()


def get_topic_attempt_counts(db: Session, limit: int = 3, least: bool = False):
    order_clause = func.count(func.distinct(models.CourseInteraction.user_id))
    if least:
        order_clause = order_clause.asc()
    else:
        order_clause = order_clause.desc()

    query = (
        db.query(
            models.Topic.id,
            models.Topic.title,
            func.count(func.distinct(models.CourseInteraction.user_id)).label(
                "user_count"
            ),
        )
        .join(models.Course, models.Course.topic_id == models.Topic.id)
        .join(
            models.CourseInteraction,
            models.CourseInteraction.course_id == models.Course.id,
        )
        .group_by(models.Topic.id)
        .order_by(order_clause)
        .limit(limit)
    )

    return query.all()


def get_quizzes_count(db: Session) -> int:
    return db.query(models.SectionQuiz).count()


def get_quizzes_completion_stats(db: Session):
    total_quizzes = db.query(models.SectionQuiz).count()
    total_passed = (
        db.query(models.CourseSectionQuizProgress)
        .filter(models.CourseSectionQuizProgress.passed == True)
        .count()
    )

    completion_rate = 0
    if total_quizzes > 0:
        completion_rate = (total_passed / total_quizzes) * 100

    return total_passed, round(completion_rate, 2)


def get_daily_new_users_last_7_days(db: Session):
    today = datetime.now(timezone.utc).date()
    seven_days_ago = today - timedelta(days=6)

    results = (
        db.query(
            cast(models.User.created_at, DATE).label("date"),
            func.count(models.User.id).label("user_count"),
        )
        .filter(cast(models.User.created_at, DATE) >= seven_days_ago)
        .group_by("date")
        .order_by("date")
        .all()
    )

    counts_by_date = {record.date.isoformat(): record.user_count for record in results}

    daily_counts = []
    for i in range(7):
        day = seven_days_ago + timedelta(days=i)
        daily_counts.append(
            {"date": day.isoformat(), "count": counts_by_date.get(day.isoformat(), 0)}
        )

    return daily_counts
