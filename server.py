from fastapi import FastAPI
from src.api.routes import router
import uvicorn

# Initialize FastAPI
app = FastAPI(title="AI Job Matcher API")

# Include Routes
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)