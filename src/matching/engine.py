import os
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
import logging

logger = logging.getLogger(__name__)

class JobPool:
    def __init__(self, csv_path, vector_engine):
        self.vector_engine = vector_engine
        self.df = pd.read_csv(csv_path).fillna('')
        
        # إنشاء مسار لملف التخزين (بنفس اسم ملف الـ CSV لكن بصيغة .npy)
        self.cache_path = csv_path.replace('.csv', '_vectors.npy')
        
        if os.path.exists(self.cache_path):
            logger.info(f"--- Loading Job Index from Cache: {self.cache_path} ---")
            self.vectors = np.load(self.cache_path)
            # تأكد أن عدد المتجهات يطابق عدد الأسطر في حال تم تعديل الـ CSV
            if len(self.vectors) != len(self.df):
                logger.warning("Cache mismatch! Re-indexing jobs...")
                self._create_and_save_index()
        else:
            self._create_and_save_index()

    def _create_and_save_index(self):
        logger.info("--- Creating New Job Index (This happens once) ---")
        texts = self.df['description'].tolist()
        self.vectors = self.vector_engine.model.encode(texts, show_progress_bar=True)
        np.save(self.cache_path, self.vectors)
        logger.info(f"--- Index Saved to: {self.cache_path} ---")

    def get_top_matches(self, user_vector, top_n=5):
        similarities = cosine_similarity(user_vector.reshape(1, -1), self.vectors)[0]
        top_indices = similarities.argsort()[-top_n:][::-1]
        
        results = []
        for idx in top_indices:
            results.append({
                "job_title": self.df.iloc[idx].get('title', 'N/A'),
                "company": self.df.iloc[idx].get('company_name', 'N/A'),
                "description": self.df.iloc[idx].get('description', ''),
                "score": round(float(similarities[idx]) * 100, 2)
            })
        return results

class CandidatePool:
    def __init__(self, csv_path, vector_engine):
        self.vector_engine = vector_engine
        self.df = pd.read_csv(csv_path).fillna('')
        self.cache_path = csv_path.replace('.csv', '_vectors.npy')
        
        if os.path.exists(self.cache_path):
            logger.info(f"--- Loading Candidate Index from Cache ---")
            self.vectors = np.load(self.cache_path)
        else:
            self._create_and_save_index()

    def _create_and_save_index(self):
        logger.info("--- Creating New Candidate Index ---")
        texts = self.df['skills_required'].tolist()
        self.vectors = self.vector_engine.model.encode(texts, show_progress_bar=True)
        np.save(self.cache_path, self.vectors)

    def get_top_candidates(self, job_vector, top_n=5):
        similarities = cosine_similarity(job_vector.reshape(1, -1), self.vectors)[0]
        top_indices = similarities.argsort()[-top_n:][::-1]
        
        results = []
        for idx in top_indices:
            results.append({
                "name": self.df.iloc[idx].get('job_position_name', 'Candidate'),
                "score": round(float(similarities[idx]) * 100, 2)
            })
        return results