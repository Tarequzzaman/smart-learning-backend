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


# from app.dependencies.auth import get_current_active_user  # Import from auth setup


router = APIRouter()


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


"""
All the topic related API here 
"""

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


""" 
Users APIs 

"""


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

    code = str(random.randint(100000, 999999))
    user = crud.get_user_by_email(db = db, email=email)
    if not user:
        raise HTTPException(status_code=404, detail="No active user found with this email.")
    crud.delete_old_pending_code(db=db, user_id=user.id)
    expiry_time =  datetime.now() + timedelta(minutes=10)
    user_name = f'{user.first_name} {user.last_name}'
    try:
        email_helper.send_email(email, code , user_name)
        crud.insert_log_in_code(
            db=db,
            code=code,
            user_id=user.id,
            expiry_time=expiry_time
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

    crud.reseat_password(db=db, user=user, password=new_password)

    return {"message": "Password reset successfully."}
