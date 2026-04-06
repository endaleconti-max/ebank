import httpx

from app.config import settings


class ReconciliationClient:
    def __init__(self) -> None:
        self.base_url = settings.reconciliation_base_url.rstrip("/")

    async def run_reconciliation(self, headers: dict) -> httpx.Response:
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.post(
                f"{self.base_url}/v1/reconciliation/runs",
                headers=headers,
            )

    async def get_reconciliation_run(self, run_id: str, headers: dict) -> httpx.Response:
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.get(
                f"{self.base_url}/v1/reconciliation/runs/{run_id}",
                headers=headers,
            )