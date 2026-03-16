import os
from openai import OpenAI
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
api_key = os.getenv("API_KEY")
api_url = os.getenv("BASE_URL")
print(f"{api_url}: {api_key}")

client = OpenAI(
    api_key=api_key,
    base_url=api_url.rstrip('/')
)

try:
    response = client.models.list()
    print("Available models:")
    for model in response.data:
        print(f"- {model.id}")
except Exception as e:
    print(f"Connection failed: {e}")
