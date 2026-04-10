import httpx

from app.config import settings


class RiskClient:
    def __init__(self) -> None:
        self.base_url = settings.risk_base_url.rstrip("/")

    async def list_rules(self, headers: dict) -> httpx.Response:
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.get(f"{self.base_url}/v1/risk/rules", headers=headers)

    async def create_rule(self, payload: dict, headers: dict) -> httpx.Response:
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.post(
                f"{self.base_url}/v1/risk/rules", json=payload, headers=headers
            )

    async def delete_rule(self, rule_id: str, headers: dict) -> httpx.Response:
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.delete(
                f"{self.base_url}/v1/risk/rules/{rule_id}", headers=headers
            )

    async def list_log(self, params: dict, headers: dict) -> httpx.Response:
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.get(
                f"{self.base_url}/v1/risk/log", params=params, headers=headers
            )

    async def evaluate(self, payload: dict, headers: dict) -> httpx.Response:
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.post(
                f"{self.base_url}/v1/risk/evaluate", json=payload, headers=headers
            )
