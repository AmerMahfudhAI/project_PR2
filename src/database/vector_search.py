import os
from typing import List, Dict, Any
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime

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
    
    def create_chat_session(self, user_id: str, session_id: str, title: str):
        """إنشاء جلسة شات جديدة في قاعدة البيانات"""
        session_doc = {
            "session_id": session_id,
            "user_id": user_id,
            "title": title,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        self.db.chat_sessions.insert_one(session_doc)

    def update_session_timestamp(self, session_id: str):
        """تحديث تاريخ آخر استخدام للجلسة"""
        self.db.chat_sessions.update_one(
            {"session_id": session_id},
            {"$set": {"updated_at": datetime.utcnow()}}
        )

    def save_chat_message(self, user_id: str, session_id: str, role: str, message: str):
        """تعديل دالة حفظ الرسالة لتشمل session_id"""
        msg_doc = {
            "user_id": user_id,
            "session_id": session_id,
            "role": role,
            "message": message,
            "timestamp": datetime.utcnow()
        }
        self.db.chat_messages.insert_one(msg_doc)

    def get_chat_history(self, user_id: str, session_id: str):
        """جلب تاريخ المحادثة لجلسة معينة ومستخدم معين فقط"""
        cursor = self.db.chat_messages.find(
            {"user_id": user_id, "session_id": session_id}
        ).sort("timestamp", 1)
        
        history = []
        for doc in cursor:
            history.append({
                "role": doc.get("role"),
                "content": doc.get("message")
            })
        return history

    def get_user_sessions(self, user_id: str):
        """جلب قائمة كل الجلسات الخاصة بـ user_id معين"""
        cursor = self.db.chat_sessions.find(
            {"user_id": user_id}
        ).sort("updated_at", -1)
        
        sessions = []
        for doc in cursor:
            sessions.append({
                "session_id": doc.get("session_id"),
                "title": doc.get("title", "محادثة جديدة"),
                "updated_at": doc.get("updated_at").isoformat() if doc.get("updated_at") else None
            })
        return sessions

    def get_session_messages(self, session_id: str):
        """جلب كافة الرسائل لجلسة محددة عند النقر عليها"""
        cursor = self.db.chat_messages.find(
            {"session_id": session_id}
        ).sort("timestamp", 1)
        
        messages = []
        for doc in cursor:
            messages.append({
                "role": doc.get("role"),
                "message": doc.get("message"),
                "timestamp": doc.get("timestamp").isoformat() if doc.get("timestamp") else None
            })
        return messages