import pandas as pd
import numpy as np
import logging
import os

logger = logging.getLogger(__name__)

def safe_clean_text(text):

    if pd.isna(text) or str(text).strip() == "" or str(text).lower() == "nan":
        return None
    return str(text).strip()

class JobPool:
    def __init__(self, csv_path, vector_engine):
        self.vector_engine = vector_engine
        self.job_vectors = np.array([])
        self.df = pd.DataFrame()

        if not os.path.exists(csv_path):
            logger.error(f"File not found: {csv_path}")
            return
            

        full_df = pd.read_csv(csv_path)

        col = 'description' if 'description' in full_df.columns else full_df.columns[3]
        

        self.df = full_df[full_df[col].apply(lambda x: isinstance(x, str) and len(x) > 10)].head(100).copy()
        
        logger.info(f"Indexing {len(self.df)} clean job entries...")
        
        vectors = []
        for text in self.df[col]:
            v = self.vector_engine.create_embedding(text)
            vectors.append(v)
            
        self.job_vectors = np.vstack(vectors) 
        logger.info("Job Indexing Successful.")

    def get_top_matches(self, user_vector, top_n=5):
        from sklearn.metrics.pairwise import cosine_similarity
        if self.job_vectors.size == 0: return []
        similarities = cosine_similarity(user_vector.reshape(1, -1), self.job_vectors)[0]
        top_indices = similarities.argsort()[-top_n:][::-1]
        
        return [
            {
                "job_title": self.df.iloc[idx].get('title', 'N/A'),
                "score": f"{round(float(similarities[idx]) * 100, 2)}%"
            } for idx in top_indices
        ]

class CandidatePool:
    def __init__(self, csv_path, vector_engine):
        self.vector_engine = vector_engine
        self.candidate_vectors = np.array([])
        
        if not os.path.exists(csv_path): return
            
        full_df = pd.read_csv(csv_path)

        col = 'skills_required' if 'skills_required' in full_df.columns else full_df.columns[1]
        

        self.df = full_df[full_df[col].apply(lambda x: isinstance(x, str) and len(x) > 5)].head(100).copy()
        
        logger.info(f"Indexing {len(self.df)} clean candidate entries...")
        
        vectors = []
        for text in self.df[col]:
            v = self.vector_engine.create_embedding(text)
            vectors.append(v)
            
        if vectors:
            self.candidate_vectors = np.vstack(vectors)
            logger.info("Candidate Indexing Successful.")

    def get_top_candidates(self, job_vector, top_n=5):
        from sklearn.metrics.pairwise import cosine_similarity
        if self.candidate_vectors.size == 0: return []
        similarities = cosine_similarity(job_vector.reshape(1, -1), self.candidate_vectors)[0]
        top_indices = similarities.argsort()[-top_n:][::-1]
        
        return [
            {
                "position": self.df.iloc[idx].get('﻿job_position_name', 'Candidate'),
                "match_score": f"{round(float(similarities[idx]) * 100, 2)}%"
            } for idx in top_indices
        ]