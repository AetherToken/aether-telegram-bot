import asyncio
import httpx


async def main():
    async with httpx.AsyncClient(
        trust_env=False,
        timeout=30,
    ) as client:
        response = await client.get(
            "https://api.telegram.org"
        )

        print("Status:", response.status_code)


asyncio.run(main())

