import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage
from src.ai_review.models import StructuredResumeResponse, JobMatchResultSchema

# Load environment variables securely from .env file
load_dotenv()

class AIResumeReviewer:
    def __init__(self):
        """
        Initializes the LangChain ChatGroq LLM instance using Llama 3.3.
        Sets up structured chains and conversational configuration.
        """
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is not configured in the environment variables.")
        
        # Initialize the high-performance Llama 3.3 model via LangChain
        self.llm = ChatGroq(
            groq_api_key=self.api_key,
            model_name="llama-3.3-70b-versatile",
            temperature=0.1  # Low temperature ensures factual and reliable extraction
        )

        # Create structured runnable chains that enforce the Pydantic schemas
        self.resume_analyzer_chain = self.llm.with_structured_output(StructuredResumeResponse)
        self.job_matcher_chain = self.llm.with_structured_output(JobMatchResultSchema)

    def get_review(self, resume_text: str) -> dict:
        """
        Analyzes the raw resume text using LangChain and extracts structured information.
        """
        if not resume_text or not resume_text.strip():
            return {"error": "Provided resume text is completely empty."}

        prompt = f"""
        You are an expert AI Resume Analyzer and ATS Optimization specialist.
        Your task is to parse the raw resume text provided below and extract all relevant information into the requested structured format.
        
        CRITICAL LANGUAGE RULE: 
        1. Automatically detect the primary language of the resume text.
        2. Provide the 'ai_overall_evaluation' field in the SAME detected language.
        
        Resume Content to Analyze:
        -------------------------
        {resume_text[:4000]}
        -------------------------
        """
        try:
            structured_data = self.resume_analyzer_chain.invoke(prompt)
            return structured_data.model_dump()
        except Exception as e:
            return {"error": f"LangChain Analysis Error: {str(e)}"}

    def match_resume_to_job(self, resume_text: str, job_description: str) -> dict:
        """
        Compares a candidate's resume text against a specific job description.
        """
        if not resume_text or not job_description:
            return {"error": "Both resume text and job description are required for matching."}

        prompt = f"""
        You are an advanced corporate Recruiter AI. Compare the given Resume text with the Job Description (JD).
        Evaluate the alignment based on industry standards, utilizing these specific weights:
        - Skills Alignment: 60%
        - Professional Experience: 30%
        - Educational Background: 10%

        LANGUAGE RULE: Write the textual 'explanation' in the same language as the provided Resume.

        Job Description (JD):
        {job_description}

        Candidate Resume:
        {resume_text[:3000]}
        """
        try:
            match_result = self.job_matcher_chain.invoke(prompt)
            return match_result.model_dump()
        except Exception as e:
            return {"error": f"LangChain Matching Error: {str(e)}"}

    def resume_coach_chat(self, user_message: str, chat_history_list: list) -> str:
        """
        AI Resume Coach that manages conversational history using LangChain message structures.
        Guides the user on how to improve, update, and fix their CV interactively.
        """
        # Convert stored flat list database dicts into actual LangChain Message Objects
        formatted_messages = []
        for msg in chat_history_list:
            if msg["role"] == "user":
                formatted_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                formatted_messages.append(AIMessage(content=msg["content"]))

        # Append the latest user prompt message at the end of the conversation history
        formatted_messages.append(HumanMessage(content=user_message))

        # System instructions given dynamically within the conversation context
        system_instructions = """
        You are an expert Career Coach AI. Your job is to help the user optimize their resume, guide them through website updates, and provide actionable tips to increase their ATS score.
        - Analyze any changes they claim to make on their profile.
        - Be professional, encouraging, and clear.
        - Respond in the same language used by the user.
        """
        
        # Insert the system instructions prefix smoothly
        messages_with_system = [HumanMessage(content=system_instructions)] + formatted_messages

        try:
            # Invoke the full conversational chain maintaining strict contextual awareness
            response = self.llm.invoke(messages_with_system)
            return response.content
        except Exception as e:
            return f"Error generation chat advice: {str(e)}"