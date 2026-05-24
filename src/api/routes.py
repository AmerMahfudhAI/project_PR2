from fastapi import APIRouter, UploadFile, File, Form
import os
import shutil
import json


from src.parser.document_parser import get_document_text as extract_text
from src.ai_review.reviewer import AIResumeReviewer
from src.matching.engine import JobPool, CandidatePool
from src.embedding.vector_creator import VectorEngine

router = APIRouter()


v_engine = VectorEngine()
reviewer = AIResumeReviewer()


try:
    job_pool = JobPool("data/postings.csv", v_engine)
    candidate_pool = CandidatePool("data/resume_data.csv", v_engine)
except Exception as e:
    print(f"Error loading pools: {e}")

@router.post("/analyze-resume")
async def analyze_resume(file: UploadFile = File(...)):
    
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        text = extract_text(temp_path)
 
        result = reviewer.get_review(text)
        return {"status": "success", "analysis": result}
    finally:
        if os.path.exists(temp_path): os.remove(temp_path)

@router.post("/match-specific-job")
async def match_job(file: UploadFile = File(...), job_description: str = Form(...)):

    temp_path = f"match_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        text = extract_text(temp_path)
        comparison = reviewer.match_resume_to_job(text, job_description)
        return {"status": "success", "comparison": comparison}
    finally:
        if os.path.exists(temp_path): os.remove(temp_path)