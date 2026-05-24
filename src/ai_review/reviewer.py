import os
import json
from dotenv import load_dotenv
from groq import Groq  # استيراد مكتبة Groq الجديدة
from src.ai_review.models import StructuredResume, JobMatchResult

load_dotenv()

class AIResumeReviewer:
    def __init__(self):
        # إعداد الاتصال بـ Groq
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        # نستخدم موديل Llama-3.3-70b لأنه خارق في التحليل وسريع جداً
        self.model_id = "llama-3.3-70b-versatile" 

    def get_review(self, resume_text: str):
        if not resume_text:
            return {"error": "Resume text is empty"}

        prompt = f"""
        Analyze the following resume text and extract information into a structured JSON format.
        LANGUAGE RULE: Detect resume language. Respond in the SAME language for 'ai_overall_evaluation'.
        
        Resume Content:
        {resume_text[:4000]}

        Return ONLY a JSON object:
        {{
            "full_name": "", "email": "", "phone": "", "linkedin": "", "github": "", "location": "",
            "summary": "", "skills": [], "languages": [],
            "education_history": [], "work_history": [], "projects": [],
            "ai_overall_evaluation": "Detailed professional review in detected language",
            "ats_score": 0,
            "detected_language": "ar/en"
        }}
        """

        try:
            # استدعاء Groq بدلاً من Gemini
            chat_completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model_id,
                response_format={"type": "json_object"} # إجبار الموديل على إرجاع JSON
            )
            
            raw_data = json.loads(chat_completion.choices[0].message.content)
            structured_data = StructuredResume(**raw_data)
            return structured_data.dict()
        except Exception as e:
            return {"error": f"Groq Error: {str(e)}"}

    def match_resume_to_job(self, resume_text: str, job_description: str):
        prompt = f"""
        Compare Resume with Job Description. 
        Weights: Skills 60%, Experience 30%, Education 10%.
        Response Language: Match input language.

        JD: {job_description}
        Resume: {resume_text[:3000]}

        Return JSON:
        {{
            "match_percentage": 0,
            "matching_skills": [],
            "missing_skills": [],
            "section_scores": {{"skills": 0, "experience": 0, "education": 0}},
            "explanation": ""
        }}
        """
        try:
            completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model_id,
                response_format={"type": "json_object"}
            )
            return json.loads(completion.choices[0].message.content)
        except Exception as e:
            return {"error": str(e)}