from app.core.config import get_settings
from app.core.container import build_container

s = get_settings()
c = build_container(s)
headers = c.vectors.client._client._rest_headers
print("Qdrant URL            :", s.qdrant_url)
print("Key in .env/settings  :", bool(s.qdrant_api_key), "(length", len(s.qdrant_api_key), ")")
print("Key sent by the app   :", "api-key" in headers)