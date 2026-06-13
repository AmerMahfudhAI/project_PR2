import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from src.ai_review.models import StructuredResumeResponse

load_dotenv()

class AIResumeReviewer:
    def __init__(self):
        """Initializes the Gemini model using LangChain framework with high stability settings."""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set in the environment variables.")
            
        # إضافة إعدادات الاستقرار لتفادي الفصل المفاجئ:
        # max_retries=3 تعني إذا فصل السيرفر سيعيد المحاولة حتى 3 مرات تلقائياً قبل إعطاء خطأ
        # timeout=60 يمنح السيرفر دقيقة كاملة لمعالجة الملفات الكبيرة
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=api_key,
            temperature=0.2,
            max_retries=3,
            timeout=60
        )
        
        self.structured_llm = self.llm.with_structured_output(StructuredResumeResponse)

    def get_review(self, resume_text: str) -> StructuredResumeResponse:
        """
        [الفكرة الأولى والثانية] تحليل نص السيرة الذاتية عبر LangChain واستخراج 
        البيانات كاملة مع الـ ATS Score بأعلى دقة وبأي لغة مع مقاومة انقطاع السيرفر.
        """
        prompt = f"""
        You are an expert ATS (Applicant Tracking System) and professional recruiter.
        Analyze the following resume text carefully, regardless of its language (Arabic, English, etc.).
        
        Extract all relevant details matching the schema provided.
        Critically evaluate the resume to compute an accurate 'ats_score' (from 0 to 100) based on industry standards, formatting, language clarity, and structure.
        
        Resume text to analyze:
        \"\"\"{resume_text}\"\"\"
        """
        try:
            response = self.structured_llm.invoke(prompt)
            return response
        except Exception as e:
            return {"error": f"Failed to analyze resume via LangChain: {str(e)}"}
    
    def extract_skills_from_job_description(self, job_description: str) -> list:
        """
        [الفكرة الثالثة] قراءة وصف الوظيفة واستخراج المهارات الأساسية والتقنية
        المطلوبة منها على شكل قائمة (List) نظيفة لتسهيل عملية المقارنة.
        """
        prompt = f"""
        You are an expert technical recruiter. Analyze the following Job Description and extract a clean list of required core skills and technologies.
        Return ONLY a JSON array of strings containing the skills. Do not include any explanation or markdown formatting.
        
        Job Description:
        \"\"\"{job_description}\"\"\"
        """
        try:
            # نستخدم الموديل الأساسي لاستخراج مصفوفة نصوص مباشرة
            response = self.llm.invoke(prompt)
            # تنظيف الخرج وتحويله إلى قائمة بايثون بأمان
            content = response.content.strip()
            if content.startswith("```json"):
                content = content.replace("```json", "").replace("```", "").strip()
            elif content.startswith("```"):
                content = content.replace("```", "").strip()
                
            import json
            skills = json.loads(content)
            return [s.lower().strip() for s in skills if isinstance(s, str)]
        except Exception:
            # في حال حدوث أي خطأ، نرجع قائمة فارغة لضمان عدم توقف السيرفر
            return []
    def generate_coach_response(self, user_message: str, resume_context: str) -> str:
        """
        [الفكرة الرابعة] توليد رد ذكي من الـ AI كـ Career Coach بناءً على 
        رسالة المستخدم الحالية وبيانات سيرته الذاتية المخزنة.
        """
        prompt = f"""
        You are an expert Career Coach and IT Recruiter. Your job is to guide the candidate, help them improve their resume, give interview tips, and suggest skills to learn.
        
        Candidate's Resume Context (Use this to customize your tips):
        \"\"\"{resume_context}\"\"\"
        
        User Message: "{user_message}"
        
        Respond kindly, professionally, and directly in the same language used by the user (Arabic or English). Keep your advice actionable and concise. Do not use any markdown code blocks or system logs.
        """
        try:
            response = self.llm.invoke(prompt)
            return response.content.strip()
        except Exception as e:
            return f"عذراً، واجهت مشكلة في الاتصال بالمستشار الذكي: {str(e)}"