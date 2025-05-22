import aiohttp
import asyncio
import json
from dotenv import load_dotenv
import os
import sys
from app.loger_setup import get_logger


logger = get_logger(__name__, level="ERROR")

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

load_dotenv()

API_KEY = os.getenv('TOKEN_DEEPSEEK')
API_URL = 'https://openrouter.ai/api/v1/chat/completions'


async def generate_text(text: str) -> str:
    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    }

    data = {
        "model": "deepseek/deepseek-r1:free",  # Убедись, что модель актуальна
        "messages": [{"role": "user", "content": text}]
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(API_URL, json=data, headers=headers) as response:
            logger.debug(f"Status: {response.status}")
            logger.debug(f"Response Text: {await response.text()}")
            if response.status == 200:
                response_json = await response.json()
                ai_text = response_json.get("choices", [{}])[0].get("message", {}).get("content", "")
                ai_text = ai_text.strip()
                if ai_text.startswith("```") and ai_text.endswith("```"):
                    lines = ai_text.splitlines()
                    if len(lines) >= 3:
                        ai_text = "\n".join(lines[1:-1]).strip()
                return ai_text
            else:
                logger.error(f"Failed to fetch data from API. Status Code: {response.status}")


async def main():
    result = await generate_text("Расскажи анекдот")
    print(result)


if __name__ == '__main__':
    asyncio.run(main())
