from pydantic import BaseModel, EmailStr
from typing import Union

class UserCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    first_name: str
    last_name: str
    role: str
    is_active: bool

    class Config:
        orm_mode = True

class TokenWithUser(BaseModel):
    access_token: str
    token_type: str
    user: dict  # or

class LogInUser(BaseModel):
    email: str
    password: str



class TopicCreate(BaseModel):
    title: str
    description: str
    created_by: int


class TokenData(BaseModel):
    email: Union[str, None] = None