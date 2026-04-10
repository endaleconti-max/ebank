import httpx

from app.config import settings


class LedgerClient:
    def __init__(self) -> None:
        self.base_url = settings.ledger_base_url.rstrip("/")

    async def create_account(self, payload: dict, headers: dict) -> httpx.Response:
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.post(
                f"{self.base_url}/v1/ledger/accounts", json=payload, headers=headers
            )

    async def get_balance(self, account_id: str, headers: dict) -> httpx.Response:
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.get(
                f"{self.base_url}/v1/ledger/accounts/{account_id}/balance", headers=headers
            )

    async def get_entry(self, entry_id: str, headers: dict) -> httpx.Response:
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.get(
                f"{self.base_url}/v1/ledger/entries/{entry_id}", headers=headers
            )
