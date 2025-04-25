from pydantic import BaseModel, EmailStr, Field
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
        from_attributes = True

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

class TopicResponse(TopicCreate):
    id: int
    created_by_id: int

    class Config:
        from_attributes = True

class TokenData(BaseModel):
    email: Union[str, None] = None



class CreatorInfo(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str

    class Config:
        from_attributes = True

class TopicResponse(BaseModel):
    id: int
    title: str
    description: str
    created_by: CreatorInfo = Field(..., alias="creator")  

    class Config:
        from_attributes = True
        validate_by_name = True


