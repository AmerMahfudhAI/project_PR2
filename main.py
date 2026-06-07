import os
import shutil
import logging
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

# Import our production-ready custom modules
from src.parser.document_parser import get_document_text
from src.ai_review.reviewer import AIResumeReviewer
from src.database.vector_search import MongoVectorSearcher

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the advanced FastAPI Application
app = FastAPI(
    title="Enterprise AI Recruitment & Conversational Coach API",
    description="Advanced FastAPI backend engineered with LangChain, Llama 3.3, and MongoDB Atlas.",
    version="2.5.0"
)

# Enable global CORS for secure cross-origin resource sharing with Laravel/Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instantiate our engines globally to ensure high performance and optimal memory usage
ai_reviewer = AIResumeReviewer()
db_searcher = MongoVectorSearcher()

@app.post("/analyze-resume", status_code=status.HTTP_200_OK)
async def analyze_resume(resume_id: str = Form(...), file: UploadFile = File(...)):
    """
    Parses an uploaded CV file, processes it via LangChain, and stores the structured matrix into MongoDB.
    """
    temp_filename = f"temp_{resume_id}_{file.filename}"
    with open(temp_filename, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        extracted_text = get_document_text(temp_filename)
        if not extracted_text:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, 
                detail="Could not extract text from the document."
            )

        structured_analysis = ai_reviewer.get_review(extracted_text)
        if "error" in structured_analysis:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=structured_analysis["error"])

        db_success = db_searcher.save_structured_resume(resume_id, structured_analysis)
        if not db_success:
            logger.warning(f"Database save failed for resume ID: {resume_id}")

        return {
            "status": "success",
            "resume_id": resume_id,
            "analysis": structured_analysis
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)


@app.post("/match-candidate-to-jobs", status_code=status.HTTP_200_OK)
async def match_candidate_to_jobs(resume_id: str = Form(...), limit: int = Form(5)):
    """
    [FOR CANDIDATES] Fetches the stored resume from the cloud, and executes a cross-check 
    against all active job posts to find the most compatible job roles.
    """
    try:
        # Retrieve the user's structured resume from MongoDB
        resume_doc = db_searcher.resumes_collection.find_one({"_id": resume_id})
        if not resume_doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume profile not found in database.")
        
        candidate_skills = resume_doc.get("skills", [])
        
        # Query MongoDB cloud pipeline to fetch top matching jobs
        matched_jobs = db_searcher.find_jobs_for_resume(candidate_skills=candidate_skills, limit=limit)
        
        return {
            "status": "success",
            "resume_id": resume_id,
            "matches_found": len(matched_jobs),
            "jobs": [
                {
                    "job_id": str(job.get("_id")),
                    "title": job.get("title", "Untitled Position"),
                    "company": job.get("company", "Generic Company"),
                    "matched_skills_score": job.get("matched_skills_count", 0)
                } for job in matched_jobs
            ]
        }
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.post("/match-job-to-candidates", status_code=status.HTTP_200_OK)
async def match_job_to_candidates(job_description: str = Form(...), limit: int = Form(5)):
    """
    [FOR COMPANIES] Processes a raw Job Description, extracts its requirements, 
    and searches MongoDB cloud database for the most fitting candidate profiles.
    """
    try:
        # Utilize our structured match tool to extract required skills dynamically
        temp_match = ai_reviewer.match_resume_to_job(resume_text="Placeholder text", job_description=job_description)
        required_skills = temp_match.get("missing_skills", [])
        
        if not required_skills:
            required_skills = [skill.strip() for skill in job_description.split(",") if len(skill.strip()) > 1]

        # Scan the resumes collection via database aggregation
        top_candidates = db_searcher.find_candidates_for_job(required_skills=required_skills, limit=limit)

        return {
            "status": "success",
            "extracted_requirements": required_skills,
            "candidates": [
                {
                    "resume_id": cand.get("_id"),
                    "full_name": cand.get("full_name", "Anonymous"),
                    "matched_skills_score": cand.get("matched_skills_count", 0),
                    "skills": cand.get("skills", [])
                } for cand in top_candidates
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.post("/resume-coach-chat", status_code=status.HTTP_200_OK)
async def resume_coach_chat(user_id: str = Form(...), message: str = Form(...)):
    """
    [AI COACH] Conversational interview assistant. Fetches chat logs from cloud history, 
    generates contextual advice on resume updates, and updates the session history safely.
    """
    try:
        # 1. Fetch persistent chat logs from cloud history to keep conversation memory context
        history = db_searcher.get_chat_history(user_id=user_id)
        
        # 2. Invoke conversational Llama 3.3 chain maintaining full behavioral awareness
        ai_advice = ai_reviewer.resume_coach_chat(user_message=message, chat_history_list=history)
        
        # 3. Synchronize history logs back to MongoDB Atlas (Save both user message and AI response)
        db_searcher.save_chat_message(user_id=user_id, role="user", message=message)
        db_searcher.save_chat_message(user_id=user_id, role="assistant", message=ai_advice)
        
        return {
            "status": "success",
            "user_id": user_id,
            "response": ai_advice
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))