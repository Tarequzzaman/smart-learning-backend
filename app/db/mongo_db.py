
from config import  get_mongo_cred
from pymongo import MongoClient

MONGO_CRED = get_mongo_cred()
MONGO_USER = MONGO_CRED.MONGO_INITDB_ROOT_USERNAME
MONGO_PASS = MONGO_CRED.MONGO_INITDB_ROOT_PASSWORD
MONGO_DB = MONGO_CRED.MONGO_DB_NAME

MONGO_HOST = "mongo"  # This is the docker-compose service name
MONGO_PORT = 27017

MONGO_URI = f"mongodb://{MONGO_USER}:{MONGO_PASS}@{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB}?authSource=admin"

print(MONGO_URI)
client = MongoClient(MONGO_URI)
mongodb_client = client[MONGO_DB]