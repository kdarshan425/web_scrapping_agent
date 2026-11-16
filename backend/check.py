import asyncio
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine
from qdrant_client import AsyncQdrantClient
from app.core.config import get_settings

async def main():
    s = get_settings()
    u = make_url(s.database_url)
    print("DB host:", u.host, "| user:", u.username, "| db:", u.database)
    print("Qdrant:", s.qdrant_url, "| key set:", bool(s.qdrant_api_key))
    try:
        async with create_async_engine(s.database_url).connect() as c:
            print("POSTGRES OK:", (await c.execute(text("select 1"))).scalar())
    except Exception as e:
        print("POSTGRES FAILED:", repr(e))
    try:
        q = AsyncQdrantClient(url=s.qdrant_url, api_key=s.qdrant_api_key or None)
        print("QDRANT OK:", await q.get_collections())
    except Exception as e:
        print("QDRANT FAILED:", repr(e))

asyncio.run(main())