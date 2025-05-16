from .celery_app import celery_app
from app.services import ai_helper
from app.db import crud
from app.db.database import SessionLocal  # your sessionmaker
from app.db.mongo_db import mongodb_client
from tqdm import tqdm
from loguru import logger


db = SessionLocal() 

@celery_app.task
def create_course_for_topic(topic_id: int, topic_name: str, description: str):
    courses = ai_helper.generate_courses(topic_name, description)
    logger.info("====== Fetch course done =====")

    for course in tqdm(courses):
        try:
            # --- Start new course ---
            course_title = course.get('title')
            course_level = course.get('course_level')
            course_description = course.get('description')

            # Create the course in SQL DB
            db_course = crud.create_course(
                db=db,
                course_title=course_title,
                course_level=course_level,
                course_description=course_description,
                topic_id=topic_id
            )
            
            course_id = db_course.id

            logger.info(f"[Course: {course_title}] SQL course created (ID: {course_id})")

            # Prepare the course object for MongoDB
            full_course = {
                "course_title": course_title,
                "course_level": course_level,
                "sections": []
            }

            # 1️⃣ Generate Course Structure (Sections + Subsections)
            try:
                sections_data = ai_helper.generate_course_structure(course_title, course_description)
                logger.info(f"[Course: {course_title}] Sections generated successfully.")
            except Exception as e:
                logger.error(f"Error generating sections for '{course_title}': {e}")
                # Skip this course and move to next
                continue

            # 2️⃣ Generate Content for Each Subsection
            for section_index, section in enumerate(tqdm(sections_data)):
                section_title = section["section_title"]
                subsections   = []

                logger.info(f"Generating content for section: {section_title}")
                for subsection_title in section["subsection_titles"]:
                    try:
                        content = ai_helper.generate_section_content(
                            course_title,
                            course_level,
                            section_title,
                            subsection_title
                        )
                        subsections.append({
                            "title": subsection_title,
                            "content": content
                        })
                        logger.info(f"✅ Content generated for subsection: {subsection_title}")
                    except Exception as e:
                        logger.error(f"Error generating content for subsection '{subsection_title}': {e}")
                        raise

                # Join subsection content into one string
                section_text = "\n\n".join(sub["content"] for sub in subsections)

                # Generate quiz from section content
                try:
                    quiz_items = ai_helper.generate_quiz_from_text(
                        section_title=section_title,
                        raw_markdown=section_text,
                    )
                    logger.info(f"✅ Quiz generated for section: {section_title}")

                    # Save each quiz question to PostgreSQL
                    for item in quiz_items:
                        crud.insert_quiz_question(
                            db=db,
                            course_id=course_id,
                            section_index=section_index,
                            question=item["question"],
                            options=item["options"],
                            correct_answer=item["correctAnswer"],
                            hint=item.get("hint")
                        )
                except Exception as e:
                    logger.warning(f"⚠️ Skipping quiz for section '{section_title}' due to error: {e}")

                full_course["sections"].append({
                    "section_title": section_title,
                    "subsections": subsections
                })


            if len(full_course.get('sections', [])) > 0:
                mongo_doc = {'course_id': course_id, 'course_details': full_course}
                mongodb_client.courses.insert_one(mongo_doc)
                logger.info(f"✅ Full course saved to MongoDB (course_id: {course_id})")

                crud.mark_course_as_built(db, course_id=course_id)
                logger.info(f"✅ Course marked as built in SQL (course_id: {course_id})")
            else: 
                logger.info(f"Error generate subsection {course})")

        except Exception as e:
            logger.error(f"🔥 Unexpected error while processing course '{course_title}': {e}")
            # Do NOT mark as complete, just continue to next course
            continue
