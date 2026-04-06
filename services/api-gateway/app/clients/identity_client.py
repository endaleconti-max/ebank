import httpx

from app.config import settings


class IdentityClient:
    def __init__(self) -> None:
        self.base_url = settings.identity_base_url.rstrip("/")

    async def create_user(self, payload: dict, headers: dict) -> httpx.Response:
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.post(f"{self.base_url}/v1/users", json=payload, headers=headers)

    async def get_user(self, user_id: str, headers: dict) -> httpx.Response:
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.get(f"{self.base_url}/v1/users/{user_id}", headers=headers)

    async def get_user_status(self, user_id: str, headers: dict) -> httpx.Response:
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.get(f"{self.base_url}/v1/users/{user_id}/status", headers=headers)

    async def submit_kyc(self, user_id: str, payload: dict, headers: dict) -> httpx.Response:
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.post(
                f"{self.base_url}/v1/users/{user_id}/kyc/submit",
                json=payload,
                headers=headers,
            )
