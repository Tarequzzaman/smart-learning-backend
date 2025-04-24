from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    DB_NAME: str 
    DB_PASSWORD: str
    DB_HOST: str
    DB_USER: str 

    class Config:
        env_file = ".env"

        
@lru_cache
def get_settings():
    return Settings()


