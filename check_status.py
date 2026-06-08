import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")

video_id = "video_6a1d621c69ac8191bc9fb1ba72e0b1350cfb9c30a58a7cb0"

response = requests.get(
    f"https://api.proxyapi.ru/openai/v1/videos/{video_id}",
    headers={
        "Authorization": f"Bearer {API_KEY}"
    }
)

print(response.json())