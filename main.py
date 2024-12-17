from fastapi import FastAPI
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pydantic import BaseModel, Field
from datetime import datetime
import os
import uuid
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")

client = MongoClient(MONGO_URI, server_api=ServerApi("1"))
db = client[DB_NAME]
click_logs = db["click_logs"]

# Initialize FastAPI
app = FastAPI()


class VisitData(BaseModel):
    userId: str = Field(..., description="User ID")
    provenance: str = Field(..., description="Provenance of the visit")
    firstVisit: datetime = Field(..., description="Timestamp of the first visit")
    counter: int = Field(..., description="Number of visits")
    durationPerSession: list = Field(
        ..., description="List of timestamps and its duration spent on the page"
    )


@app.post("/log/visit/")
async def log_visit(userId: str, provenance: str):
    # verify if user exists in the database
    user = click_logs.find_one({"userId": userId})
    if user is None:
        userId = str(uuid.uuid4())

        log_entry = VisitData(
            userId=userId,
            provenance=provenance,
            durationPerSession=[],
            counter=1,
            firstVisit=datetime.now(),
        )
        result = click_logs.insert_one(log_entry.model_dump())
        log_id = str(result.inserted_id)

    else:
        result = click_logs.update_one({"userId": userId}, {"$inc": {"counter": 1}})
        log_id = user["_id"]

    return {"status": "success", "log_id": str(log_id)}


@app.post("/log/timespent/")
async def log_time_spent(duration: str, userId: str):
    user = click_logs.find_one({"userId": userId})

    if user is None:
        return {"status": "error", "message": "User not found"}

    result = click_logs.update_one(
        {"userId": userId},
        {
            "$push": {
                "durationPerSession": {"timestamp": datetime.now(), "duration": duration}
            }
        },
    )
    return {"status": "success", "log_id": str(result)}


@app.get("/logs/")
async def get_logs():
    logs = click_logs.find()
    return {"status": "success", "logs": list(logs)}