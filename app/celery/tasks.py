from .celery_app import celery_app
from app.services import ai_helper
from app.db import crud
from app.db.database import SessionLocal  # your sessionmaker


@celery_app.task
def create_course_for_topic( topic_id: int, topic_name: str, description: str):
    db = SessionLocal() 
    courses = ai_helper.generate_courses(topic_name, description)
    for course in courses:
        crud.create_course(
            db=db,
            course_title=course.get('title'),
            course_level=course.get('course_level'),
            course_description= course.get('description'),
            topic_id=topic_id
        )






