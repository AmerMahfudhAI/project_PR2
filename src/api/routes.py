from fastapi import APIRouter, UploadFile, File, HTTPException
import os
import shutil

from src.parser.document_parser import get_document_text as extract_text
from src.ai_review.reviewer import AIResumeReviewer
from src.database.connection import MongoDBConnection

router = APIRouter()
reviewer = AIResumeReviewer()
db_conn = MongoDBConnection()

@router.post("/analyze-resume")
async def analyze_resume(file: UploadFile = File(...)):
    """
    [الفكرة الأولى] استقبال ملف السيرة الذاتية فقط، تحليله عبر LangChain،
    استخراج الـ ATS Score، وحفظ البيانات تلقائياً في MongoDB Atlas مع معالجة الـ ObjectId.
    """
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # 1. استخراج النص من الملف
        text = extract_text(temp_path)
        if not text or text.strip() == "":
            raise HTTPException(status_code=422, detail="Could not extract any valid text from the document.")
            
        # 2. التحليل بواسطة الـ AI (LangChain)
        ai_response = reviewer.get_review(text)
        
        if isinstance(ai_response, dict) and "error" in ai_response:
            raise HTTPException(status_code=502, detail=ai_response["error"])

        # 3. تحويل كائن Pydantic الناتج إلى قاموس بايثون
        resume_data = (
            ai_response.dict() 
            if hasattr(ai_response, "dict") 
            else dict(ai_response)
        )

        # 4. الحفظ في كولكشن resumes
        resumes_collection = db_conn.get_collection("resumes")
        inserted_result = resumes_collection.insert_one(resume_data)
        generated_id = str(inserted_result.inserted_id)

        # ⚙️ الحل السحري: تحويل الـ ObjectId الخاص بالمونغو داخل القاموس إلى نص عادي كي يقبله FastAPI
        if "_id" in resume_data:
            resume_data["_id"] = str(resume_data["_id"])

        # 5. النتيجة النهائية الصافية بدون طباعة في التيرمنال
        return {
            "status": "success",
            "message": "Resume successfully analyzed via LangChain and saved to MongoDB Atlas.",
            "resume_id": generated_id,
            "filename": file.filename,
            "analysis": resume_data
        }
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail="An error occurred during resume analysis processing")
        
    finally:
        if os.path.exists(temp_path): 
            os.remove(temp_path)


@router.post("/match-resume-to-database-jobs")
async def match_resume_to_database_jobs(file: UploadFile = File(...)):
    """
    [الفكرة الثانية] يرفع المستخدم ملف السي في الخاص به فقط، ليتلقى قائمة 
    بالوظائف المتاحة بقاعدة البيانات مرتبة تنازلياً حسب نسبة التوافق ونسبة الـ ATS.
    """
    temp_path = f"match_db_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # 1. استخراج النص من السي في المرفوع
        text = extract_text(temp_path)
        if not text or text.strip() == "":
            raise HTTPException(status_code=422, detail="Could not extract any valid text from the document.")
            
        # 2. تحليل السي في عبر الـ AI لاستخراج مهارات المستخدم الحالي والـ ATS Score الخاص به
        ai_response = reviewer.get_review(text)
        if isinstance(ai_response, dict) and "error" in ai_response:
            raise HTTPException(status_code=502, detail=ai_response["error"])

        resume_data = ai_response.dict() if hasattr(ai_response, "dict") else dict(ai_response)
        
        # استخراج مهارات المستخدم وتحويلها لـ لور كيس للمقارنة الدقيقة
        candidate_skills = [s.lower().strip() for s in resume_data.get("skills", [])]
        candidate_ats = resume_data.get("ats_score", 50) # الـ ATS الأساسي للمرشح

        # 3. جلب جميع الوظائف المتاحة من كولكشن job_posts في المونغو
        jobs_collection = db_conn.get_collection("job_posts")
        all_jobs = list(jobs_collection.find())
        
        matched_results = []
        
        # 4. حساب نسب التطابق برمجياً لكل وظيفة
        for job in all_jobs:
            job_skills = [s.lower().strip() for s in job.get("skills", [])]
            
            # تقاطع المهارات (المهارات المشتركة بين السي في والوظيفة)
            intersected_skills = set(candidate_skills).intersection(set(job_skills))
            matched_skills_count = len(intersected_skills)
            
            total_job_skills = len(job_skills)
            match_percentage = 0
            if total_job_skills > 0:
                match_percentage = int((matched_skills_count / total_job_skills) * 100)
            
            # حساب نسبة الـ ATS الخاصة بالوظيفة بناءً على وزن المهارات والـ ATS الأساسي للسي في
            # معادلة ذكية تدمج قوة السي في مع نسبة المهارات المطلوبة للوظيفة
            job_ats_compatibility = int((match_percentage * 0.6) + (candidate_ats * 0.4))
            
            # بناء كائن الوظيفة النظيف بالتسميات المطلوبة
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
            
        # 5. ترتيب الوظائف تنازلياً من الأعلى توافقاً إلى الأقل
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
        
    finally:
        if os.path.exists(temp_path): 
            os.remove(temp_path)


from fastapi import Form # تأكد من وجود Form في أعلى الملف مع الاستيرادات

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
            # جلب مهارات المرشح والـ ATS الأساسي له
            candidate_skills = [s.lower().strip() for s in resume.get("skills", [])]
            candidate_ats = resume.get("ats_score", 50)
            
            # حساب تقاطع المهارات المشتركة
            intersected_skills = set(candidate_skills).intersection(set(required_job_skills))
            matched_skills_count = len(intersected_skills)
            
            # حساب نسبة التوافق العامة
            match_percentage = 0
            if total_job_skills > 0:
                match_percentage = int((matched_skills_count / total_job_skills) * 100)
                
            # حساب توافق الـ ATS الخاص بهذا المرشح مع هذه الوظيفة تحديداً
            job_ats_compatibility = int((match_percentage * 0.6) + (candidate_ats * 0.4))
            
            # بناء كائن المرشح النظيف للشركة
            candidate_item = {
                "resume_id": str(resume.get("_id")),
                # جلب الاسم الشخصي المخزن في الـ CV، أو وضع اسم افتراضي
                "candidate_name": resume.get("personal_info", {}).get("name", "Qualified Candidate") if isinstance(resume.get("personal_info"), dict) else "Qualified Candidate",
                "matched_skills_count": matched_skills_count,
                "match_percentage": f"{match_percentage}%",
                "ats_compatibility_score": f"{job_ats_compatibility}%"
            }
            matched_candidates.append(candidate_item)
            
        # 4. ترتيب المرشحين تنازلياً من النسبة الأعلى للأسفل
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


@router.post("/resume-coach-chat")
async def resume_coach_chat(message: str = Form(...)):
    """
    [الفكرة الرابعة] محادثة ذكية مباشرة مع مستشار التوظيف (Chatbot).
    يتعرف النظام تلقائياً على مهاراتك من آخر سي في قمت برفعه ويوجهك بذكاء.
    """
    try:
        # 1. جلب آخر سيرة ذاتية مرفوعة في قاعدة البيانات لتدعيم الـ AI بسياق المستخدم
        resumes_collection = db_conn.get_collection("resumes")
        # جلب آخر مستند تم إدخاله بترتيب عكسي للـ _id
        latest_resume = resumes_collection.find_one(sort=[("_id", -1)])
        
        resume_context = ""
        if latest_resume:
            # تحويل الـ id لنص لتفادي أي مشاكل
            latest_resume["_id"] = str(latest_resume["_id"])
            resume_context = str(latest_resume)
        else:
            resume_context = "No resume uploaded yet. Treat the user as a general job seeker."

        # 2. توليد الرد من الكوتش الذكي بالاعتماد على سياق السي في والرسالة
        ai_response = reviewer.generate_coach_response(message, resume_context)
        
        # 3. إرجاع الرد النظيف فوراً للفرونت إند
        return {
            "status": "success",
            "response": ai_response
        }
        
    except Exception:
        raise HTTPException(status_code=500, detail="An error occurred in the chat coach assistant")