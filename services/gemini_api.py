import asyncio
import aiohttp
import os
import sys
from dotenv import load_dotenv
from app.loger_setup import get_logger

logger = get_logger(__name__, level="INFO")

load_dotenv()

API_KEY = os.getenv('TOKEN_GEMINI')
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

async def generate_text(text: str) -> str:
    async with aiohttp.ClientSession() as session:
        headers = {'Content-Type': 'application/json'}
        payload = {"contents": [{"parts": [{"text": text}]}]}
        params = {'key': API_KEY}

        try:
            async with session.post(API_URL, json=payload, headers=headers, params=params) as response:
                raw_text = await response.text()
                if response.status != 200:
                    logger.error(f"API error {response.status}: {raw_text}")
                    return "⚠️ Ошибка API. Попробуйте позже."

                response_json = await response.json()
                resp = response_json["candidates"][0]["content"]["parts"][0]["text"].strip()

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
    response = await generate_text('напиши короткую шутку')
    print("Ответ от нейросети:", response)


if __name__ == '__main__':
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
