import asyncio
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import VectorParams, Distance
from app.core.config import get_settings

async def main():
    s = get_settings()
    q = AsyncQdrantClient(url=s.qdrant_url, api_key=s.qdrant_api_key or None, check_compatibility=False)
    try:
        print("exists:", await q.collection_exists("company_policies"))
    except Exception as e:
        print("EXISTS FAILED:", e)
    try:
        await q.create_collection("test_perm", vectors_config=VectorParams(size=4, distance=Distance.COSINE))
        print("CREATE OK")
        await q.delete_collection("test_perm")
    except Exception as e:
        print("CREATE FAILED:", e)
    await q.close()

asyncio.run(main())