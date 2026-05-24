from pydantic import BaseModel, Field
from typing import List, Optional, Any

class Education(BaseModel):
    institution: Optional[str] = None
    degree: Optional[str] = None
    year: Optional[str] = None

class WorkExperience(BaseModel):
    company: Optional[str] = None
    role: Optional[str] = Field(None, alias="job_title") 
    duration: Optional[str] = None
    description: Optional[str] = None

    class Config:
        populate_by_name = True 

class StructuredResume(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    location: Optional[str] = None
    summary: Optional[str] = None
    skills: Any = None 
    languages: Any = None
    education_history: List[Education] = Field(default_factory=list)
    work_history: List[WorkExperience] = Field(default_factory=list)
    projects: List[Any] = Field(default_factory=list)
    ai_overall_evaluation: str
    ats_score: Optional[int] = 0

class JobMatchResult(BaseModel):
    match_percentage: int
    matching_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    section_scores: dict = Field(default_factory=lambda: {"skills": 0, "experience": 0, "education": 0})
    explanation: str