from fastapi import APIRouter, status, Security
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from app.db import crud, schemas, database
from sqlalchemy.orm import Session
from app.services import auth, email_helper
from app.celery.tasks import create_course_for_topic
from fastapi.responses import JSONResponse
from typing import Annotated, List
import random
from datetime import datetime, timedelta
from app.db.mongo_db import mongodb_client
from app.services.password_helper import get_password_hash , verify_password


# from app.dependencies.auth import get_current_active_user  # Import from auth setup


router = APIRouter()


@router.get("/users/{user_id}/completed-courses", response_model=List[schemas.CourseResponse])
def get_completed_courses(
    user_id: int,
    db: Session = Depends(database.get_db),
    current_user: schemas.UserOut = Depends(auth.get_current_active_user)
):
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own completed courses."
        )

    completed_courses = crud.get_completed_courses(db=db, user_id=user_id)

    if not completed_courses:
        return []

    return completed_courses


@router.get("/users/{user_id}/selected-topics", response_model=List[schemas.TopicResponse])
def get_user_selected_topics(
    user_id: int,
    db: Session = Depends(database.get_db),
    current_user: schemas.UserOut = Depends(auth.get_current_active_user)
):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="You can only get your own selected topics.")
    
    selected_topics = crud.get_user_selected_topics(db, user_id=user_id)
    return selected_topics


@router.put("/users/update/{user_id}", response_model=schemas.UserOut)
def update_user(
    user_id: int,
    user_update: schemas.UserUpdateDetails,  
    db: Session = Depends(database.get_db),
    current_user: schemas.UserOut = Depends(auth.get_current_active_user) 
):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="You can only update your own profile.")
    
    user = crud.get_user(db=db, user_id=user_id)
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    print(f"Updating User ID: {user_id}")
    print(f"Current User: {current_user}")
    print(f"User Details to Update: {user_update}")

    # Update the user information in the database
    updated_user = crud.update_user_details(db=db, user=user, user_update=user_update)

    print(f"Updated User: {updated_user}")

    return updated_user




@router.post("/users/", response_model=schemas.UserOut)
def create_user(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    try:
        db_user = crud.get_user_by_email(db, email=user.email)
        if db_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        crud.create_user(db=db, user=user)
        return JSONResponse({'detail': 'User successfully created Please Log in using same credentials'}, status_code=201)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Email already registered")


@router.post("/log_in", response_model=schemas.TokenWithUser)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends()
 ,
    db: Session = Depends(database.get_db)
):
    user = crud.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    access_token = auth.create_access_token(
        data={"sub": user.email}
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
        }
    }



@router.post("/register/send-code")
async def send_registration_code(
    request: schemas.ForgotPasswordRequest,  
    db: Session = Depends(database.get_db),
):
    email = request.email

    user = crud.get_user_by_email(db=db, email=email)
    if user:
        raise HTTPException(status_code=400, detail="User already exists with this email.")

    code = str(random.randint(100000, 999999))
    
    expiry_time = datetime.now() + timedelta(minutes=10)

    try:
        email_helper.send_registration_email(email, code, "New User Registration")

        crud.insert_log_in_code(
            db=db,
            code=code,
            user_id=None,  
            expiry_time=expiry_time,
            email=email,  
        )

        return {"message": "Verification code sent to your email address."}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send registration code: {str(e)}")
    


@router.post("/register/verify-code")
async def verify_registration_code(
    request: schemas.VerifyResetCodeRequest,  
    db: Session = Depends(database.get_db),
):
    email = request.email
    code = request.code

    reset_entry = crud.get_pending_code_by_email(db=db, email=email)
    if not reset_entry:
        raise HTTPException(status_code=404, detail="No pending registration code found for this email.")
    
    if reset_entry.code != code:
        raise HTTPException(status_code=400, detail="Invalid code.")
    
    if reset_entry.expiry_time < datetime.now():
        raise HTTPException(status_code=400, detail="Code expired.")
    
    crud.accept_reset_code(db=db, reset_entry=reset_entry)


    return {"message": "Code verified successfully. Proceed with your registration."}

@router.get("/users/interests", response_model=schemas.UserInterestsStatus)
def get_user_interests_status(
    db: Session = Depends(database.get_db),
    current_user: schemas.UserOut = Depends(auth.get_current_active_user),
):
    interests = crud.get_user_interests(db, user_id=current_user.id)
    return {"hasInterests": bool(interests)}  


@router.post("/users/topic-preference")
def add_user_topic_preferences(
    preference_data: schemas.TopicPreferenceRequest,  
    db: Session = Depends(database.get_db),
    current_user: schemas.UserOut = Depends(auth.get_current_active_user)
):
    topic_ids = preference_data.topic_ids
    preferences = crud.add_user_topic_preferences(db=db, user_id=current_user.id, topic_ids=topic_ids)
    return {"message": f"User has shown interest in topics: {', '.join(map(str, [preference.topic_id for preference in preferences]))}"}


@router.post("/topics", response_model=schemas.TopicResponse, status_code=status.HTTP_201_CREATED)
async def create_topic(
    current_user: Annotated[schemas.UserOut, Depends(auth.get_current_active_user)],
    topic: schemas.TopicCreate,
    db: Session = Depends(database.get_db),
):
    if not current_user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user")
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have admin permissions",
        )
    topic = crud.create_topic(db=db, topic=topic, user_id= current_user.id)
    create_course_for_topic.delay(topic.id, topic.title, topic.description) ## add background process for courses
    return topic




@router.get("/topics", response_model=List[schemas.TopicResponse])
def get_all_topics(
    db: Session = Depends(database.get_db),
):
    
    return crud.get_all_topics(db)



@router.put("/topics/{topic_id}", response_model=schemas.TopicResponse)
def update_topic(
    topic_id: int,
    topic_data: schemas.TopicCreate,
    db: Session = Depends(database.get_db),
    current_user: schemas.UserOut = Depends(auth.get_current_active_user)
):
    if not current_user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user")
    
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have admin permissions",
        )
    
    db_topic = crud.get_topic_by_id(db, topic_id)
    if not db_topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    return crud.update_topic(db, db_topic, topic_data)


@router.delete("/topics/{topic_id}", status_code=204)
def delete_topic(
    topic_id: int,
    db: Session = Depends(database.get_db),
    current_user: schemas.UserOut = Depends(auth.get_current_active_user)
):
    if not current_user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user")
    
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have admin permissions",
        )
    
    topic = crud.get_topic_by_id(db, topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    crud.delete_topic(db, topic)
    return 



@router.get("/users", response_model=List[schemas.UserOut])
def get_all_users(
    db: Session = Depends(database.get_db),
    current_user: schemas.UserOut = Depends(auth.get_current_active_user),
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have admin permissions",
        )

    return crud.get_all_users(db)




@router.put("/users/{user_id}", response_model=schemas.UserOut)
def update_user(
    user_id: int,
    user_update: schemas.UserUpdate,
    db: Session = Depends(database.get_db),
    current_user: schemas.UserOut = Depends(auth.get_current_active_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    user = crud.get_user(db=db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return crud.update_user(db, user, user_update)


@router.delete("/users/{user_id}", status_code=204)
def delete_user_route(
    user_id: int,
    db: Session = Depends(database.get_db),
    current_user: schemas.UserOut = Depends(auth.get_current_active_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="You do not have admin permissions")

    user = crud.get_user_by_id(db=db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return crud.delete_user(db=db, user=user)






@router.post("/forgot-password/send-code")
async def send_forgot_password_code(
    request: schemas.ForgotPasswordRequest,

    db: Session = Depends(database.get_db),
    ):
    email = request.email
    print("users email",email)

    code = str(random.randint(100000, 999999))
    user = crud.get_user_by_email(db = db, email=email)
    if not user:
        raise HTTPException(status_code=404, detail="No active user found with this email.")
    crud.delete_old_pending_code(db=db, user_id=user.id)
    expiry_time =  datetime.now() + timedelta(minutes=10)
    user_name = f'{user.first_name} {user.last_name}'
    try:
        email_helper.send_email(email, code , user_name)
        crud.insert_log_in_code_forgot_password(
            db=db,
            code=code,
            user_id=user.id,
            expiry_time=expiry_time,
        )
        return {"message": "Reset code sent to your email address."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send reset code: {str(e)}")


@router.post("/forgot-password/verify-code")
async def verify_reset_code(
    request: schemas.VerifyResetCodeRequest,
    db: Session = Depends(database.get_db),
):
    email = request.email
    code = request.code
    user = crud.get_user_by_email(db=db, email=email)
    if not user:
        raise HTTPException(status_code=404, detail="No active user found with this email.")
    reset_entry = crud.get_pending_code_by_user(db=db, user_id=user.id)
    if not reset_entry or reset_entry.code != code:
        raise HTTPException(status_code=400, detail="Invalid code.")
    if reset_entry.expiry_time < datetime.now():
        raise HTTPException(status_code=400, detail="Code expired.")
    crud.accept_reset_code(db=db, reset_entry=reset_entry)  # mark as accepted
    return {"message": "Reset code verified successfully."}


@router.post("/forgot-password/reset-password")
async def reset_password(request: schemas.ResetPasswordRequest, db: Session = Depends(database.get_db)):
    email = request.email
    new_password = request.password
    user = crud.get_user_by_email(db=db, email=email)
    if not user:
        raise HTTPException(status_code=404, detail="No active user found.")
    if verify_password(new_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="New password cannot be the same as the current password.")

    
    crud.reseat_password(db=db, user=user, password=new_password)
    return {"message": "Password reset successfully."}


@router.get("/courses/{course_id}")
def get_full_course(
    course_id: int, 
    current_user: schemas.UserOut = Depends(auth.get_current_active_user), 
    db: Session = Depends(database.get_db)            
    ):
    """
    Fetch the full course content from MongoDB by course_id.
    """
    course_doc = mongodb_client.courses.find_one({"course_id": course_id})
    user_id=current_user.id
    course_interaction_detail = crud.get_course_interaction(db, course_id, user_id)
    if not course_doc:
        raise HTTPException(status_code=404, detail="Course not found")
    total_sections = len(course_doc['course_details']["sections"])
    quiz_status = {str(i): False for i in range(total_sections)}   # "0": False, "1": False …
    passed_rows = crud.get_passed_quiz_section(db=db, user_id=current_user.id, course_id=course_id)
    for row in passed_rows:
        quiz_status[str(row.section_index)] = True                 # flip to True
    course_doc['course_details']["quiz_status"] = quiz_status
    course_doc["_id"] = str(course_doc["_id"])
    course_doc['course_details']['course_progress'] = course_interaction_detail.get('course_progress', 0)
    return course_doc['course_details']


@router.get("/courses", response_model=List[schemas.CourseOut])
def get_ai_generated_courses(
    db: Session = Depends(database.get_db),
    current_user: schemas.UserOut = Depends(auth.get_current_active_user),
):
    return  crud.get_all_courses(db=db)


@router.get("/topics/{topic_id}/courses")
def get_courses_by_topic(
    topic_id: int,
    db: Session = Depends(database.get_db),
    current_user: schemas.UserOut = Depends(auth.get_current_active_user),
):
    topic = crud.get_topic_by_id(db=db, topic_id=topic_id)
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Topic not found"
        )

    
    courses = crud.get_courses_by_topics(
        db=db,
        topic_ids=[topic_id],
        exclude_course_ids=[],
        limit=30
    )

    return {
        "topic": {
            "id": topic.id,
            "title": topic.title,
            "description": topic.description,
        },
        "courses": courses
    }



@router.get("/mycourses", response_model=List[schemas.CourseWithCourseProgress])
def get_enrolled_courses(
    user_id: int, 
    db: Session = Depends(database.get_db),
    current_user: schemas.UserOut = Depends(auth.get_current_active_user),
):
    results =   crud.get_enrolled_courses(db=db, user_id=user_id)
    return [
        schemas.CourseWithCourseProgress(
            id=course.id,
            course_title=course.course_title,
            course_description=course.course_description,
            course_level=course.course_level,
            is_published=course.is_published,
            is_detail_created_by_ai=course.is_detail_created_by_ai,
            topic_id=course.topic_id,
            course_progress=interaction.course_progress
        )
        for course, interaction in results
    ]



@router.get("/recommendations",response_model=List[schemas.CourseOut])
def get_recommendations_for_user(
    user_id: int,
    limit: int = 48,
    db: Session = Depends(database.get_db), 
    current_user: schemas.UserOut = Depends(auth.get_current_active_user),
    ):
  
    user_interests = crud.get_user_interested_topics(db, user_id)
    enrolled_course_tuples = crud.get_enrolled_courses(db=db, user_id=user_id)
    enrolled_course_ids = [course.id for course, _ in enrolled_course_tuples]    


    # 3️⃣ Get topics of enrolled courses
    enrolled_topics = crud.get_topic_ids_from_enrolled_courses(db, user_id)
    courses = []
    strategy = ""

    # ✅ SCENARIO 1: No interests + no enrollments
    if not user_interests and not enrolled_topics:
        strategy = "random_trending"
        print(strategy)
        courses = crud.get_random_courses(db, limit=limit)

    # ✅ SCENARIO 2: No interests + has enrollments
    elif not user_interests and enrolled_topics:
        strategy = "related_to_enrollments"
        courses = crud.get_courses_by_topics(
            db,
            topic_ids=enrolled_topics,
            exclude_course_ids=enrolled_course_ids,  # Just in case, though no enrollments.
            limit=limit
        )

    # ✅ SCENARIO 3: Has interests + no enrollments
    elif user_interests and not enrolled_topics:
        strategy = "interest_based"
        courses = crud.get_courses_by_topics(
            db,
            topic_ids=user_interests,
            exclude_course_ids=enrolled_course_ids,  # Just in case, though no enrollments.
            limit=limit
        )

    # ✅ SCENARIO 4: Has interests + has enrollments
    else:
        strategy = "hybrid_interest_and_enrollment"
        interest_courses = crud.get_courses_by_topics(
            db,
            topic_ids=user_interests,
            exclude_course_ids=enrolled_course_ids,
            limit=limit // 2
        )
        related_courses = crud.get_courses_by_topics(
            db,
            topic_ids=enrolled_topics,
            exclude_course_ids=enrolled_course_ids,
            limit=limit - len(interest_courses)
        )
        courses = interest_courses + related_courses
    return courses



@router.post("/enroll")
def enroll_in_course(
    enroll_data: schemas.Enroll,
    db: Session = Depends(database.get_db), 
    current_user: schemas.UserOut = Depends(auth.get_current_active_user),
):
    """
    Enroll the logged-in user in a course (safer).
    """
    crud.create_course_interaction(db, user_id=enroll_data.user_id, course_id=enroll_data.course_id)
    return {"status": "success"}


@router.put("/courses/update_progress")
def update_course_progress(
    payload: schemas.CourseProgressUpdate,
    db: Session = Depends(database.get_db),
    current_user: schemas.UserOut = Depends(auth.get_current_active_user),

):
    user_id=current_user.id
    return crud.update_course_progress(
        db=db,
        user_id=user_id,
        course_id=payload.course_id,
        new_progress=payload.progress
    )


@router.get("/section-quizzes")
def get_section_quizzes(
    course_id: int,
    section_index: int ,
    db: Session = Depends(database.get_db),
    current_user: schemas.UserOut = Depends(auth.get_current_active_user),

):
    quizzes = crud.get_quizes(db=db, course_id=course_id, section_index=section_index);
    return [
        {
            "id": q.id,
            "question": q.data.get("question"),
            "options": q.data.get("options"),
            "correctAnswer": q.data.get("correctAnswer"),
            "hint": q.data.get("hint")
        }
        for q in quizzes
    ]


@router.post("/courses/{course_id}/sections/{section_index}/quiz-complete", status_code=204)
def mark_quiz_complete(
    course_id: int,
    section_index: int,
    db: Session = Depends(database.get_db),
    current_user: schemas.UserOut = Depends(auth.get_current_active_user),
):
    crud.mark_quiz_passed(
        db=db, user_id=current_user.id, course_id=course_id, section_index=section_index
    )

   
# Admin Analytics Endpoint

@router.get("/dashboard/stats")
def get_dashboard_stats(
    db: Session = Depends(database.get_db),
    current_user: schemas.UserOut = Depends(auth.get_current_active_user),
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have admin permissions",
        )
    
    user_count = crud.get_users_count(db)
    topic_count = crud.get_topics_count(db)
    most_attempted = crud.get_topic_attempt_counts(db, limit=3, least=False)
    least_attempted = crud.get_topic_attempt_counts(db, limit=3, least=True)
    
    quiz_count = crud.get_quizzes_count(db) 
    
    passed_quizzes, completion_rate = crud.get_quizzes_completion_stats(db)
    daily_new_users = crud.get_daily_new_users_last_7_days(db)

    

    return {
        "user_count": user_count,
        "topic_count": topic_count,
        "most_attempted": [
        {"title": t[1], "user_count": t[2]} for t in most_attempted
    ],
    "least_attempted": [
        {"title": t[1], "user_count": t[2]} for t in least_attempted
    ],
        "quiz_count": quiz_count,
        
        "passed_quizzes": passed_quizzes,
        "completion_rate": completion_rate,
        "daily_new_users": daily_new_users

        
    }