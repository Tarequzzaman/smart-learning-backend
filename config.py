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
        extra = Extra.ignore  # ✅ allow unrelated fields



@lru_cache
def get_settings():
    return Settings()



@lru_cache
def get_jwt_token_cred():
    return JWT_Token()


