import os
from dotenv import load_dotenv, find_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

def test_api_availability():
    load_dotenv(find_dotenv())
    
    api_key = os.getenv("API_KEY")
    base_url = os.getenv("BASE_URL")
    model_name = "qwen3-235b-a22b"
    
    llm = ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        max_tokens=10
    )
    
    try:
        response = llm.invoke([HumanMessage(content="Hello")])
        print("API Status: OK")
        print(response.content)
        return True
    except Exception as e:
        print("API Status: UNAVAILABLE")
        print(e)
        return False

if __name__ == "__main__":
    test_api_availability()
