from fastapi import APIRouter, status, Security
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from app.db import crud, schemas, database
from sqlalchemy.orm import Session
from app.services import auth
from fastapi.responses import JSONResponse
from typing import Annotated, List

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
    return crud.create_topic(db=db, topic=topic, user_id= current_user.id)



@router.get("/topics", response_model=List[schemas.TopicResponse])
def get_all_topics(
    db: Session = Depends(database.get_db),
    # current_user: schemas.UserOut = Depends(auth.get_current_active_user)
):
    # if not current_user.is_active:
    #     raise HTTPException(status_code=403, detail="Inactive user")
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





