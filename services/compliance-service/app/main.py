from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(
    title="Compliance Service",
    description="Sanctions watchlist screening and audit log",
    version="0.1.0",
)

app.include_router(router)
