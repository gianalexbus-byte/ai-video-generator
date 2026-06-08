import os
import time
import threading
import requests
import telebot
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_KEY")
BASE_URL = "https://api.proxyapi.ru/openai/v1"

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env")

if not API_KEY:
    raise ValueError("API_KEY не найден в .env")

bot = telebot.TeleBot(BOT_TOKEN)

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

user_tasks = {}


def update_progress_message(user_id, message_id, status, progress, message_text):
    try:
        bar_length = 20
        filled_length = int((progress / 100) * bar_length)
        bar = "█" * filled_length + "░" * (bar_length - filled_length)

        status_emoji = {
            "queued": "⏳",
            "in_progress": "⚙️",
            "downloading": "⬇️",
            "completed": "✅",
            "failed": "❌",
            "error": "❌",
            "started": "🚀",
        }

        emoji = status_emoji.get(status, "⏳")
        text = f"{emoji} {message_text}\n\n[{bar}] {progress:.1f}%"

        bot.edit_message_text(
            text,
            chat_id=user_id,
            message_id=message_id
        )

    except Exception as e:
        print(f"Ошибка обновления сообщения: {e}")


def generate_video_with_progress(prompt, user_id, message_id):
    try:
        user_tasks[user_id] = {
            "status": "started",
            "progress": 0,
        }

        update_progress_message(
            user_id,
            message_id,
            "started",
            0,
            "Генерация видео началась"
        )

        create_response = requests.post(
            f"{BASE_URL}/videos",
            headers=HEADERS,
            json={
                "model": "sora-2",
                "prompt": prompt,
                "seconds": "4",
            },
        )

        print("Ответ создания:", create_response.status_code, create_response.text)
        create_response.raise_for_status()

        video = create_response.json()
        video_id = video["id"]

        while True:
            status_response = requests.get(
                f"{BASE_URL}/videos/{video_id}",
                headers=HEADERS,
            )

            print("Ответ статуса:", status_response.status_code, status_response.text)
            status_response.raise_for_status()

            video = status_response.json()
            status = video.get("status")
            progress = video.get("progress", 0) or 0

            if status == "queued":
                message_text = "Видео в очереди"
            elif status == "in_progress":
                message_text = "Видео обрабатывается"
            elif status in ("completed", "complete", "succeeded"):
                message_text = "Видео готово"
                progress = 100
            else:
                message_text = f"Статус: {status}"

            user_tasks[user_id] = {
                "status": status,
                "progress": progress,
                "video_id": video_id,
            }

            update_progress_message(
                user_id,
                message_id,
                status,
                progress,
                message_text
            )

            if status in ("completed", "complete", "succeeded"):
                break

            if status == "failed":
                raise RuntimeError(f"Генерация не удалась: {video}")

            time.sleep(5)

        update_progress_message(
            user_id,
            message_id,
            "downloading",
            95,
            "Скачивание видео..."
        )

        download_response = requests.get(
            f"{BASE_URL}/videos/{video_id}/content",
            headers={"Authorization": f"Bearer {API_KEY}"},
        )

        print("Ответ скачивания:", download_response.status_code)
        download_response.raise_for_status()

        video_path = f"video_{user_id}_{message_id}.mp4"

        with open(video_path, "wb") as file:
            file.write(download_response.content)

        with open(video_path, "rb") as video_file:
            bot.send_video(
                user_id,
                video_file,
                caption="✅ Видео готово!"
            )

        if os.path.exists(video_path):
            os.remove(video_path)

        user_tasks[user_id] = {
            "status": "completed",
            "progress": 100,
            "video_id": video_id,
        }

        update_progress_message(
            user_id,
            message_id,
            "completed",
            100,
            "✅ Генерация завершена"
        )

    except Exception as e:
        print(f"Ошибка генерации: {e}")

        user_tasks[user_id] = {
            "status": "error",
            "progress": 0,
        }

        update_progress_message(
            user_id,
            message_id,
            "error",
            0,
            "❌ Ошибка генерации видео"
        )


@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    welcome_text = """
🎬 Добро пожаловать в бота для генерации видео через ИИ!

📝 Использование:
Просто отправьте описание видео.

Пример:
Крупный план чашки кофе на деревянном столе, утренний свет.

⏱️ Генерация занимает некоторое время.
"""
    bot.reply_to(message, welcome_text)


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    prompt = message.text.strip()

    if not prompt:
        bot.reply_to(message, "❌ Пожалуйста, отправьте описание видео.")
        return

    if message.from_user.id in user_tasks:
        current_task = user_tasks[message.from_user.id]

        if current_task.get("status") in (
            "started",
            "queued",
            "in_progress",
            "downloading",
        ):
            bot.reply_to(
                message,
                "⏳ Дождитесь завершения текущей генерации."
            )
            return

    progress_msg = bot.reply_to(
        message,
        "🚀 Генерация видео началась...\n\n[░░░░░░░░░░░░░░░░░░░░] 0.0%"
    )

    thread = threading.Thread(
        target=generate_video_with_progress,
        args=(prompt, message.from_user.id, progress_msg.message_id)
    )

    thread.daemon = True
    thread.start()


if __name__ == "__main__":
    print("Бот запущен...")
    bot.infinity_polling()