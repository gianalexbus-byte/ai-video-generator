import os
import time
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
BASE_URL = "https://api.proxyapi.ru/openai/v1"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

def generate_video(prompt):
    response = requests.post(
        f"{BASE_URL}/videos",
        headers=HEADERS,
        json={
            "model": "sora-2",
            "prompt": prompt,
            "seconds": "4",
        },
    )

    print("Ответ создания:", response.status_code, response.text)
    response.raise_for_status()

    video = response.json()
    video_id = video["id"]

    print("Генерация видео началась:", video_id)

    bar_length = 30

    while True:
        status_response = requests.get(
            f"{BASE_URL}/videos/{video_id}",
            headers=HEADERS,
        )

        print("\nОтвет статуса:", status_response.status_code, status_response.text)
        status_response.raise_for_status()

        video = status_response.json()
        status = video.get("status")
        progress = video.get("progress", 0)

        filled_length = int((progress / 100) * bar_length)
        bar = "=" * filled_length + "-" * (bar_length - filled_length)

        sys.stdout.write(f"\rСтатус: {status} [{bar}] {progress}%")
        sys.stdout.flush()

        if status in ("completed", "complete", "succeeded"):
            break

        if status == "failed":
            raise RuntimeError(f"Генерация не удалась: {video}")

        time.sleep(5)

    print("\nГенерация завершена. Скачивание видео...")

    download_response = requests.get(
        f"{BASE_URL}/videos/{video_id}/content",
        headers={"Authorization": f"Bearer {API_KEY}"},
    )

    print("Ответ скачивания:", download_response.status_code)
    download_response.raise_for_status()

    with open("video.mp4", "wb") as file:
        file.write(download_response.content)

    print("Файл video.mp4 сохранён")


if __name__ == '__main__':
    generate_video(
        "A simple 4-second video of a red apple on a white table, soft light, slow camera movement."
    )
