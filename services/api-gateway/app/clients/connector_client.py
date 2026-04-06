import httpx

from app.config import settings


class ConnectorClient:
    def __init__(self) -> None:
        self.base_url = settings.connector_base_url.rstrip("/")

    async def list_transaction_events(self, params: dict, headers: dict) -> httpx.Response:
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.get(
                f"{self.base_url}/v1/connectors/transaction-events",
                params=params,
                headers=headers,
            )

    async def get_transaction(self, external_ref: str, headers: dict) -> httpx.Response:
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.get(
                f"{self.base_url}/v1/connectors/transactions/{external_ref}",
                headers=headers,
            )

    async def list_transactions(self, headers: dict) -> httpx.Response:
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.get(
                f"{self.base_url}/v1/connectors/transactions",
                headers=headers,
            )

    async def simulate_callback(self, payload: dict, headers: dict) -> httpx.Response:
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.post(
                f"{self.base_url}/v1/connectors/simulate-callback",
                json=payload,
                headers=headers,
            )
