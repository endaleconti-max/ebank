import httpx

from app.config import settings


class AliasClient:
    def __init__(self) -> None:
        self.base_url = settings.alias_base_url.rstrip("/")

    async def verify_phone(self, payload: dict, headers: dict) -> httpx.Response:
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.post(
                f"{self.base_url}/v1/aliases/verify-phone",
                json=payload,
                headers=headers,
            )

    async def bind_alias(self, payload: dict, headers: dict) -> httpx.Response:
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.post(
                f"{self.base_url}/v1/aliases/bind",
                json=payload,
                headers=headers,
            )

    async def resolve_alias(self, phone_e164: str, headers: dict) -> httpx.Response:
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.get(
                f"{self.base_url}/v1/aliases/resolve",
                params={"phone_e164": phone_e164},
                headers=headers,
            )
