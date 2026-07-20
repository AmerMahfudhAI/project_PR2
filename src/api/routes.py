import os
import shutil
import uuid
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Form, HTTPException
from src.parser.document_parser import get_document_text as extract_text
from src.ai_review.reviewer import AIResumeReviewer
from src.database.connection import MongoDBConnection

router = APIRouter()
reviewer = AIResumeReviewer()
db_conn = MongoDBConnection()

@router.post("/analyze-resume")
async def analyze_resume(
    file_url: str = Form(...),
    user_id: str = Form(...)  # 👈 أضفنا user_id هنا لتحديد صاحب السي في
):
    try:
        clean_user_id = user_id.strip().lower()
        
        text = extract_text(file_url)
        if not text or text.strip() == "":
            raise HTTPException(status_code=422, detail="Could not extract any valid text from the provided file URL.")
            
        ai_response = reviewer.get_review(text)
        if isinstance(ai_response, dict) and "error" in ai_response:
            raise HTTPException(status_code=502, detail=ai_response["error"])

        resume_data = ai_response.dict() if hasattr(ai_response, "dict") else dict(ai_response)

        resume_data["cloudinary_url"] = file_url
        resume_data["user_id"] = clean_user_id  # 👈 ربط السي في بـ user_id المعني
        resume_data["created_at"] = datetime.utcnow()

        resumes_collection = db_conn.get_collection("resumes")
        inserted_result = resumes_collection.insert_one(resume_data)
        generated_id = str(inserted_result.inserted_id)

        if "_id" in resume_data:
            resume_data["_id"] = str(resume_data["_id"])

        return {
            "status": "success",
            "message": "Resume successfully analyzed via LangChain and saved to MongoDB Atlas.",
            "user_id": clean_user_id,
            "resume_id": generated_id,
            "analysis": resume_data
        }
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail="An error occurred during resume analysis processing")
    
@router.post("/match-resume-to-database-jobs")
async def match_resume_to_database_jobs(file_url: str = Form(...)):
    """
    [الفكرة الثانية] يرسل المستخدم رابط السي في (Cloudinary URL)، ليتلقى قائمة 
    بالوظائف المتاحة بقاعدة البيانات مرتبة تنازلياً حسب نسبة التوافق.
    """
    try:
        # 1. استخراج النص من الرابط
        text = extract_text(file_url)
        if not text or text.strip() == "":
            raise HTTPException(status_code=422, detail="Could not extract any valid text from the provided file URL.")
            
        # 2. تحليل السي في عبر الـ AI واستخراج مهارات المستخدم والـ ATS Score
        ai_response = reviewer.get_review(text)
        if isinstance(ai_response, dict) and "error" in ai_response:
            raise HTTPException(status_code=502, detail=ai_response["error"])

        resume_data = ai_response.dict() if hasattr(ai_response, "dict") else dict(ai_response)
        
        candidate_skills = [s.lower().strip() for s in resume_data.get("skills", [])]
        candidate_ats = resume_data.get("ats_score", 50)

        # 3. جلب جميع الوظائف المتاحة من كولكشن job_posts
        jobs_collection = db_conn.get_collection("job_posts")
        all_jobs = list(jobs_collection.find())
        
        matched_results = []
        
        # 4. حساب نسب التطابق برمجياً
        for job in all_jobs:
            job_skills = [s.lower().strip() for s in job.get("skills", [])]
            intersected_skills = set(candidate_skills).intersection(set(job_skills))
            matched_skills_count = len(intersected_skills)
            
            total_job_skills = len(job_skills)
            match_percentage = 0
            if total_job_skills > 0:
                match_percentage = int((matched_skills_count / total_job_skills) * 100)
            
            job_ats_compatibility = int((match_percentage * 0.6) + (candidate_ats * 0.4))
            
            job_item = {
                "job_id": str(job.get("_id")),
                "title": job.get("title", "Untitled Position"),
                "company": job.get("company", "Generic Company"),
                "location": job.get("location", "Remote / N/A"),
                "matched_skills_count": matched_skills_count,
                "match_percentage": f"{match_percentage}%",
                "ats_compatibility_score": f"{job_ats_compatibility}%"
            }
            matched_results.append(job_item)
            
        matched_results.sort(key=lambda x: int(x["match_percentage"].replace("%", "")), reverse=True)
        
        return {
            "status": "success",
            "matches_found": len(matched_results),
            "recommended_jobs": matched_results
        }
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail="An error occurred during database job matching processing")

@router.post("/match-job-description-to-candidates")
async def match_job_description_to_candidates(job_description: str = Form(...)):
    """
    [الفكرة الثالثة] تضع الشركة وصف الوظيفة (Job Description) المطلوبة، لتتلقى قائمة
    بجميع السير الذاتية المخزنة في قاعدة البيانات مرتبة تنازلياً حسب نسبة التوافق.
    """
    try:
        # 1. استخراج مهارات الوظيفة المطلوبة من الوصف باستخدام الـ AI
        required_job_skills = reviewer.extract_skills_from_job_description(job_description)
        
        if not required_job_skills:
            raise HTTPException(status_code=422, detail="Could not extract any clear skills from the provided job description.")

        # 2. جلب جميع السير الذاتية المتاحة من كولكشن resumes في المونغو Atlas
        resumes_collection = db_conn.get_collection("resumes")
        all_resumes = list(resumes_collection.find())
        
        matched_candidates = []
        total_job_skills = len(required_job_skills)

        # 3. المقارنة البرمجية الرياضية بين مهارات الوظيفة وكل سي في مخزن
        for resume in all_resumes:
            candidate_skills = [s.lower().strip() for s in resume.get("skills", [])]
            candidate_ats = resume.get("ats_score", 50)
            
            intersected_skills = set(candidate_skills).intersection(set(required_job_skills))
            matched_skills_count = len(intersected_skills)
            
            match_percentage = 0
            if total_job_skills > 0:
                match_percentage = int((matched_skills_count / total_job_skills) * 100)
                
            job_ats_compatibility = int((match_percentage * 0.6) + (candidate_ats * 0.4))
            
            candidate_item = {
                "resume_id": str(resume.get("_id")),
                "candidate_name": resume.get("personal_info", {}).get("name", "Qualified Candidate") if isinstance(resume.get("personal_info"), dict) else "Qualified Candidate",
                "matched_skills_count": matched_skills_count,
                "match_percentage": f"{match_percentage}%",
                "ats_compatibility_score": f"{job_ats_compatibility}%"
            }
            matched_candidates.append(candidate_item)
            
        matched_candidates.sort(key=lambda x: int(x["match_percentage"].replace("%", "")), reverse=True)
        
        return {
            "status": "success",
            "extracted_job_skills_count": total_job_skills,
            "candidates_found": len(matched_candidates),
            "recommended_candidates": matched_candidates
        }
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail="An error occurred during candidate matching processing")

# =====================================================================
# 💬 نظام الشات المطور (دعم الجلسات المتعددة والمستخدمين)
# =====================================================================
@router.post("/resume-coach-chat")
async def resume_coach_chat(
    user_id: str = Form(...),
    message: str = Form(...),
    session_id: Optional[str] = Form(None)
):
    try:
        clean_user_id = user_id.strip().lower()
        sessions_col = db_conn.get_collection("chat_sessions")
        messages_col = db_conn.get_collection("chat_messages")
        resumes_col = db_conn.get_collection("resumes")

        # 1. إدارة الجلسات
        if not session_id or session_id.strip() == "":
            session_id = str(uuid.uuid4())
            session_title = message[:30] + "..." if len(message) > 30 else message
            
            new_session = {
                "session_id": session_id,
                "user_id": clean_user_id,
                "title": session_title,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            sessions_col.insert_one(new_session)
        else:
            sessions_col.update_one(
                {"session_id": session_id},
                {"$set": {"updated_at": datetime.utcnow()}}
            )

        # 2. 🎯 جلب السي في الخاص بهذا الـ user_id تحديداً (وليس آخر سي في في الداتابيز!)
        user_resume = resumes_col.find_one(
            {"user_id": clean_user_id}, 
            sort=[("_id", -1)]
        )

        if user_resume:
            user_resume["_id"] = str(user_resume["_id"])
            resume_context = f"User Resume Info: {str(user_resume)}"
        else:
            resume_context = f"No resume uploaded yet for user '{clean_user_id}'. Treat this user as a new general job seeker. Do NOT refer to anyone else's resume."

        # 3. توليد رد الذكاء الاصطناعي بناءً على سياق هذا المستخدم فقط
        ai_response = reviewer.generate_coach_response(message, resume_context)

        # 4. حفظ الرسائل
        messages_col.insert_one({
            "user_id": clean_user_id,
            "session_id": session_id,
            "role": "user",
            "message": message,
            "timestamp": datetime.utcnow()
        })
        messages_col.insert_one({
            "user_id": clean_user_id,
            "session_id": session_id,
            "role": "assistant",
            "message": ai_response,
            "timestamp": datetime.utcnow()
        })

        return {
            "status": "success",
            "user_id": clean_user_id,
            "session_id": session_id,
            "response": ai_response
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in chat assistant: {str(e)}")

@router.get("/users/{user_id}/sessions")
async def get_user_chat_sessions(user_id: str):
    """
    جلب كل جلسات المحادثة الخاصة بمستخدم معين (عرض القائمة الجانبية Sidebar في الفرونت إند)
    """
    try:
        clean_user_id = user_id.strip().lower()
        sessions_col = db_conn.get_collection("chat_sessions")
        
        cursor = sessions_col.find({"user_id": clean_user_id}).sort("updated_at", -1)
        sessions = []
        for doc in cursor:
            sessions.append({
                "session_id": doc.get("session_id"),
                "title": doc.get("title", "محادثة جديدة"),
                "updated_at": doc.get("updated_at").isoformat() if doc.get("updated_at") else None
            })

        return {
            "status": "success",
            "user_id": clean_user_id,
            "sessions_count": len(sessions),
            "sessions": sessions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str):
    """
    جلب كافة الرسائل لجلسة شات معينة عند النقر عليها من القائمة الجانبية
    """
    try:
        messages_col = db_conn.get_collection("chat_messages")
        cursor = messages_col.find({"session_id": session_id}).sort("timestamp", 1)
        
        messages = []
        for doc in cursor:
            messages.append({
                "role": doc.get("role"),
                "message": doc.get("message"),
                "timestamp": doc.get("timestamp").isoformat() if doc.get("timestamp") else None
            })

        return {
            "status": "success",
            "session_id": session_id,
            "messages_count": len(messages),
            "messages": messages
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))