import asyncio
import aiohttp
import os
from dotenv import load_dotenv
from app.loger_setup import get_logger

logger = get_logger(__name__, level="INFO")

load_dotenv()

API_URL = os.getenv('API_URL')

async def generate_text(text: str) -> str:
    async with aiohttp.ClientSession() as session:
        headers = {"Content-Type": "application/json"}

        payload = {
            "model": "gemma-2-9b-it",
            "messages": [
                {
                    "role": "system",
                    "content": "Ты ИИ, который разбирает портфолио и извлекает теги."
                },
                {
                    "role": "user",
                    "content": text
                }
            ],
            "temperature": 0.2,
            "max_tokens": 1024
        }

        try:
            async with session.post(API_URL, json=payload, headers=headers) as response:
                raw_text = await response.text()
                if response.status != 200:
                    logger.error(f"API error {response.status}: {raw_text}")
                    return "⚠️ Ошибка API. Попробуйте позже."

                response_json = await response.json()

                resp = response_json["choices"][0]["message"]["content"].strip()
                logger.info(f"Получен ответ от API: {resp[:100]}...")

                if resp.startswith("```") and resp.endswith("```"):
                    lines = resp.splitlines()
                    if len(lines) >= 3:
                        return "\n".join(lines[1:-1])
                    elif len(lines) == 2:
                        return lines[1].rstrip("`")
                    else:
                        return ""
                return resp

        except aiohttp.ClientError as e:
            logger.error(f"Network error: {e}")
            return "⚠️ Сетевая ошибка. Проверьте подключение."


async def main():
    response = await generate_text('напиши только код на питоне')
    print("Ответ от нейросети:", response)


if __name__ == '__main__':
    asyncio.run(main())
