import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()
api_key = os.getenv("API_KEY")
base_url = os.getenv("BASE_URL")
model_name = os.getenv("MODEL_QWEN", "Qwen 3.6 35B")

def test_model(model_id):
    try:
        llm = ChatOpenAI(
            model=model_id,
            api_key=api_key,
            base_url=base_url,
            max_retries=1
        )
        response = llm.invoke("Hello, are you there?")
        print(f"Success with {model_id}: {response.content}")
        return True
    except Exception as e:
        print(f"Failed with {model_id}: {e}")
        return False

models_to_test = [
    model_name,
    f"openai/{model_name}",
    f"qwen/{model_name}",
    "qwen/qwen-2.5-72b",
    "openai/qwen-2.5-72b",
    "Qwen/Qwen2.5-72B-Instruct",
    "openai/Qwen/Qwen2.5-72B-Instruct"
]

for m in models_to_test:
    if test_model(m):
        break
