from fastapi import APIRouter
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from app.db import crud, schemas, database
from sqlalchemy.orm import Session
from app.services import auth
from fastapi.responses import JSONResponse

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


@router.post("/topics", status_code=201)
async def create_topic(
    topic: schemas.TopicCreate,
    current_user: schemas.UserOut = Depends(auth.get_current_active_user)
):
    print(f"Creating topic by: {current_user.last_name}")

    return {
        "msg": "Topic created successfully",
        "created_by": current_user.last_name,
        "topic": topic
    }


