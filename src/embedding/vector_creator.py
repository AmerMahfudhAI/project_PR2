from sentence_transformers import SentenceTransformer
import numpy as np
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VectorEngine:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initializes the pre-trained Transformer model.
        'all-MiniLM-L6-v2' is fast and excellent for sentence/phrase embeddings.
        """
        try:
            logger.info(f"Loading transformer model: {model_name}...")
            self.model = SentenceTransformer(model_name)
            logger.info("Model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            raise

    def create_embedding(self, cleaned_text: str) -> np.ndarray:
        """
        Converts a cleaned string into a numerical vector (Embedding).
        
        Args:
            cleaned_text (str): The processed text from cleaner.
            
    Returns:
            np.ndarray: A high-dimensional vector representing the text.
        """
        if not cleaned_text:
            logger.warning("Empty text provided for embedding.")
            return np.array([])

        # Generate the embedding vector
        embedding = self.model.encode(cleaned_text)
        return embedding

if __name__ == "__main__":
    # Test the Vector Engine
    engine = VectorEngine()
    
    sample_1 = "software engineer python developer machine learning"
    sample_2 = "backend developer django flask developer"
    
    vec_1 = engine.create_embedding(sample_1)
    vec_2 = engine.create_embedding(sample_2)
    
    print(f"\nVector Shape: {vec_1.shape}") # Should be (384,)
    print(f"Sample Vector Preview: {vec_1[:5]} ...")