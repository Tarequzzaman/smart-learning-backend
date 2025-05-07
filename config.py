from pydantic_settings import BaseSettings
from functools import lru_cache
from pydantic import Extra


class Settings(BaseSettings):
    DB_NAME: str 
    DB_PASSWORD: str
    DB_HOST: str
    DB_USER: str 

    class Config:
        env_file = ".env"
        extra = Extra.ignore  # ✅ allow unrelated fields


class JWT_Token(BaseSettings):
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    ALGORITHM: str
    SECRET_KEY: str

    class Config:
        env_file = ".env"
        extra = Extra.ignore 

class EmailCredentials(BaseSettings):
    SMTP_SERVER:str
    SMTP_PORT: int
    GMAIL_USER: str
    GMAIL_PASSWORD: str

    class Config:
        env_file = ".env"
        extra = Extra.ignore  


class CeleryCredentials(BaseSettings):
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    class Config:
        env_file = ".env"
        extra = Extra.ignore 


class OpenAICredentails(BaseSettings):
    OPEN_AI_API_KEY: str

@lru_cache
def get_email_cred():
    return EmailCredentials()


@lru_cache
def get_settings():
    return Settings()


@lru_cache
def get_jwt_token_cred():
    return JWT_Token()


@lru_cache
def get_celery_cred():
    return CeleryCredentials()




@lru_cache
def get_open_ai_cred():
    return OpenAICredentails()