import os
from typing import List, Dict, Any
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

class MongoVectorSearcher:
    def __init__(self):
        """
        Initializes connections to MongoDB Atlas for Chat and Resume persistence.
        """
        self.mongo_uri = os.getenv("MONGODB_URI")
        if not self.mongo_uri:
            raise ValueError("MONGODB_URI is missing from the environment variables.")
            
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client["joboffers"]
        
        self.resumes_collection = self.db["resumes"]
        self.jobs_collection = self.db["job_posts"]
        self.chat_collection = self.db["chat_histories"]

    def save_structured_resume(self, resume_id: str, structured_data: Dict[str, Any]) -> bool:
        """Saves or updates a structured resume in the database."""
        try:
            structured_data["_id"] = resume_id
            self.resumes_collection.update_one({"_id": resume_id}, {"$set": structured_data}, upsert=True)
            return True
        except Exception:
            return False

    def save_chat_message(self, user_id: str, role: str, message: str) -> bool:
        """
        Appends a new chat message into the user's persistent cloud chat history.
        """
        try:
            self.chat_collection.update_one(
                {"_id": user_id},
                {"$push": {"messages": {"role": role, "content": message}}},
                upsert=True
            )
            return True
        except Exception:
            return False

    def get_chat_history(self, user_id: str) -> List[Dict[str, str]]:
        """Retrieves the full chat history logs for a specific user."""
        try:
            doc = self.chat_collection.find_one({"_id": user_id})
            return doc.get("messages", []) if doc else []
        except Exception:
            return []