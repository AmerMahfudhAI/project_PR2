import os
import certifi
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class MongoDBConnection:
    def __init__(self):
        """
        Initializes the MongoDB cloud connection using the URI from environment variables.
        Includes options to handle SSL handshake timeouts and VPN connections gracefully.
        """
        self.uri = os.getenv("MONGODB_URI")
        if not self.uri:
            raise ValueError("MONGODB_URI is not set in the environment variables.")
        
        # Establish the secure cloud connection with SSL bypass for VPN local testing
        self.client = MongoClient(
            self.uri, 
            tls=True,
            tlsAllowInvalidCertificates=True,  # 👈 يتجاوز مشكلة SSL Handshake عند تشغيل الـ VPN
            tlsCAFile=certifi.where(),
            connectTimeoutMS=30000,
            socketTimeoutMS=30000,
            serverSelectionTimeoutMS=30000
        )
        
        # Connect to the specific database 'joboffers'
        self.db = self.client["joboffers"]

    def get_collection(self, collection_name: str):
        """
        Retrieves a specific collection from the database.
        
        Args:
            collection_name (str): The name of the collection to fetch.
            
        Returns:
            Collection: The requested PyMongo collection object.
        """
        return self.db[collection_name]

    def close_connection(self):
        """
        Closes the connection to the MongoDB cluster safely.
        """
        self.client.close()

# Example usage interface for testing the connection independently
if __name__ == "__main__":
    try:
        print("Testing MongoDB Cloud Connection...")
        db_conn = MongoDBConnection()
        
        # Test fetching the 'job_posts' collection count
        jobs_collection = db_conn.get_collection("job_posts")
        count = jobs_collection.count_documents({})
        
        print("✅ Connection successful!")
        print(f"📊 Total documents found in 'job_posts': {count}")
        
        db_conn.close_connection()
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")