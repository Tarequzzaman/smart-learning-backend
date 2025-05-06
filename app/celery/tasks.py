from .celery_app import celery_app

@celery_app.task
def create_course_for_topic(topic_id: int, topic_name: str):
    task_id = create_course_for_topic.request.id
    print(f"received topic id {topic_id} and topic name {topic_name} and task_id {task_id}")


