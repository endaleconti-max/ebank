from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import settings
from app.middleware.idempotency import IdempotencyMiddleware
from app.middleware.request_context import RequestContextMiddleware

app = FastAPI(title=settings.service_name, version="0.1.0")
app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
if settings.enforce_idempotency:
    app.add_middleware(IdempotencyMiddleware)
app.include_router(router)
