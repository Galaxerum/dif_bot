import asyncio
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('TOKEN_GEMINI')
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
# PROXY_URL = os.getenv("PROXY_URL")
# API_URL = "https://77.34.83.3:1234/v1/chat/completions"


async def generate_text(text: str) -> str:
    async with aiohttp.ClientSession() as session:
        headers = {'Content-Type': 'application/json'}
        payload = {"contents": [{"parts": [{"text": text}]}]}
        params = {'key': API_KEY}

        async with session.post(API_URL, json=payload, headers=headers, params=params) as response:
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


async def main():
    response = await generate_text('напиши только код на питоне')
    print("Ответ от нейросети:", response)


if __name__ == '__main__':
    asyncio.run(main())
