import os
import logging
from typing import List, Dict, Any
from pymongo import MongoClient
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class MongoVectorSearcher:
    def __init__(self):
        """
        Initializes connections to MongoDB Atlas.
        Manages collections for resumes, job posts, and chat sessions.
        """
        self.mongo_uri = os.getenv("MONGODB_URI")
        if not self.mongo_uri:
            raise ValueError("MONGODB_URI is missing from the environment variables.")
            
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client["joboffers"]
        
        # Defining our core collections
        self.resumes_collection = self.db["resumes"]
        self.jobs_collection = self.db["job_posts"]
        self.chat_collection = self.db["chat_histories"]

    def save_structured_resume(self, resume_id: str, structured_data: Dict[str, Any]) -> bool:
        """Saves or updates a structured resume in the database."""
        try:
            structured_data["_id"] = resume_id
            self.resumes_collection.update_one({"_id": resume_id}, {"$set": structured_data}, upsert=True)
            return True
        except Exception as e:
            logger.error(f"Failed to save resume: {str(e)}")
            return False

    def find_jobs_for_resume(self, candidate_skills: List[str], limit: int = 5) -> List[Dict[str, Any]]:
        """
        Finds the most suitable jobs for a specific candidate based on their skills.
        Used when a user uploads their CV and wants to see matching jobs.
        """
        try:
            logger.info(f"Scanning cloud jobs for candidate skills: {candidate_skills}")
            pipeline = [
                {"$match": {"skills": {"$exists": True, "$ne": []}}},
                {
                    "$addFields": {
                        "matched_skills_count": {
                            "$size": {"$setIntersection": ["$skills", candidate_skills]}
                        }
                    }
                },
                {"$sort": {"matched_skills_count": -1}},
                {"$limit": limit}
            ]
            return list(self.jobs_collection.aggregate(pipeline))
        except Exception as e:
            logger.error(f"Error matching jobs for candidate: {str(e)}")
            return []

    def find_candidates_for_job(self, required_skills: List[str], limit: int = 5) -> List[Dict[str, Any]]:
        """
        Finds the most suitable candidates for a specific job post.
        Used when a company posts a job description and wants matching resumes.
        """
        try:
            logger.info(f"Scanning cloud resumes for job requirements: {required_skills}")
            pipeline = [
                {"$match": {"skills": {"$exists": True, "$ne": []}}},
                {
                    "$addFields": {
                        "matched_skills_count": {
                            "$size": {"$setIntersection": ["$skills", required_skills]}
                        }
                    }
                },
                {"$sort": {"matched_skills_count": -1}},
                {"$limit": limit}
            ]
            return list(self.resumes_collection.aggregate(pipeline))
        except Exception as e:
            logger.error(f"Error matching candidates for job: {str(e)}")
            return []

    def save_chat_message(self, user_id: str, role: str, message: str) -> bool:
        """
        Appends a new chat message into the user's persistent cloud chat history.
        Maintains continuity for the AI Resume Coach.
        """
        try:
            self.chat_collection.update_one(
                {"_id": user_id},
                {"$push": {"messages": {"role": role, "content": message}}},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Failed to save chat message: {str(e)}")
            return False

    def get_chat_history(self, user_id: str) -> List[Dict[str, str]]:
        """Retrieves the full chat history logs for a specific user."""
        try:
            doc = self.chat_collection.find_one({"_id": user_id})
            return doc.get("messages", []) if doc else []
        except Exception as e:
            logger.error(f"Failed to fetch chat history: {str(e)}")
            return []