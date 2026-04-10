import httpx

from app.config import settings


class ComplianceClient:
    def __init__(self) -> None:
        self.base_url = settings.compliance_base_url.rstrip("/")

    async def list_watchlist(self, headers: dict) -> httpx.Response:
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.get(
                f"{self.base_url}/v1/compliance/watchlist", headers=headers
            )

    async def create_watchlist_entry(self, payload: dict, headers: dict) -> httpx.Response:
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.post(
                f"{self.base_url}/v1/compliance/watchlist", json=payload, headers=headers
            )

    async def delete_watchlist_entry(self, entry_id: str, headers: dict) -> httpx.Response:
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.delete(
                f"{self.base_url}/v1/compliance/watchlist/{entry_id}", headers=headers
            )

    async def list_log(self, params: dict, headers: dict) -> httpx.Response:
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.get(
                f"{self.base_url}/v1/compliance/log", params=params, headers=headers
            )

    async def screen(self, payload: dict, headers: dict) -> httpx.Response:
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.post(
                f"{self.base_url}/v1/compliance/screen", json=payload, headers=headers
            )
