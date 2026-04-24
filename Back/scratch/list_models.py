import os
import logging
from google import genai
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def list_models():
    load_dotenv(dotenv_path="Back/.env")
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("Error: No GEMINI_API_KEY found in Back/.env")
        return

    print(f"Usando API Key: {api_key[:10]}...")
    
    versions = ["v1", "v1beta", "v1alpha"]
    
    for version in versions:
        print(f"\n--- Probando versión: {version} ---")
        try:
            client = genai.Client(api_key=api_key, http_options={'api_version': version})
            models = client.models.list()
            for m in models:
                print(f"- {m.name}")
        except Exception as e:
            print(f"Error en {version}: {e}")

if __name__ == "__main__":
    list_models()
