import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


test_models = [
    'gemini-1.5-flash-latest', 
    'gemini-2.0-flash-latest',
    'gemini-flash-latest'
]

for model_alias in test_models:
    try:
        print(f"--- تجربة Alias: {model_alias} ---")
        model = genai.GenerativeModel(model_alias)
        response = model.generate_content("Say hello")
        print(f"✅ نجح! الرد: {response.text}")
        break
    except Exception as e:
        print(f"❌ Falied{model_alias}: {e}\n")