import asyncio
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv('API_URL')

async def generate_text(text: str) -> str:
    async with aiohttp.ClientSession() as session:
        headers = {"Content-Type": "application/json"}

        payload = {
            "model": "gemma-2-9b-it",  # или твоя установленная модель
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

        async with session.post(API_URL, json=payload, headers=headers) as response:
            response_json = await response.json()

            # Правильный способ достать текст из ответа LM Studio
            resp = response_json["choices"][0]["message"]["content"].strip()

            # Обработка обёртки ```json
            if resp.startswith("```") and resp.endswith("```"):
                lines = resp.splitlines()
                if len(lines) >= 3:
                    return "\n".join(lines[1:-1])
                elif len(lines) == 2:
                    return lines[1].rstrip("`")
                else:
                    return ""
            return resp



async def main():
    response = await generate_text('напиши только код на питоне')
    print("Ответ от нейросети:", response)


if __name__ == '__main__':
    asyncio.run(main())
