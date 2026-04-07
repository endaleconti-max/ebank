import httpx

from app.config import settings


class OrchestratorClient:
    def __init__(self) -> None:
        self.base_url = settings.orchestrator_base_url.rstrip("/")

    async def create_transfer(self, payload: dict, headers: dict) -> httpx.Response:
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.post(f"{self.base_url}/v1/transfers", json=payload, headers=headers)

    async def get_transfer(self, transfer_id: str, headers: dict) -> httpx.Response:
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.get(f"{self.base_url}/v1/transfers/{transfer_id}", headers=headers)

    async def update_transfer_note(self, transfer_id: str, payload: dict, headers: dict) -> httpx.Response:
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.patch(
                f"{self.base_url}/v1/transfers/{transfer_id}/note",
                json=payload,
                headers=headers,
            )

    async def connector_callback(self, payload: dict, headers: dict) -> httpx.Response:
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.post(
                f"{self.base_url}/v1/transfers/callbacks/connector",
                json=payload,
                headers=headers,
            )

    async def relay_events(self, limit: int, headers: dict) -> httpx.Response:
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.post(
                f"{self.base_url}/v1/transfers/events/relay",
                params={"limit": limit},
                headers=headers,
            )

    async def list_transfers(self, params: dict, headers: dict) -> httpx.Response:
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.get(
                f"{self.base_url}/v1/transfers",
                params=params,
                headers=headers,
            )

    async def cancel_transfer(self, transfer_id: str, headers: dict) -> httpx.Response:
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.post(
                f"{self.base_url}/v1/transfers/{transfer_id}/cancel",
                headers=headers,
            )

    async def list_transfer_events(self, transfer_id: str, params: dict, headers: dict) -> httpx.Response:
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.get(
                f"{self.base_url}/v1/transfers/{transfer_id}/events",
                params=params,
                headers=headers,
            )

    async def get_transfer_event_summary(self, transfer_id: str, headers: dict) -> httpx.Response:
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.get(
                f"{self.base_url}/v1/transfers/{transfer_id}/events/summary",
                headers=headers,
            )

    async def transition_transfer(self, transfer_id: str, payload: dict, headers: dict) -> httpx.Response:
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await client.post(
                f"{self.base_url}/v1/transfers/{transfer_id}/transition",
                json=payload,
                headers=headers,
            )
