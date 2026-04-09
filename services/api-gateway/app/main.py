from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.config import settings
from app.middleware.authentication import AuthenticationMiddleware
from app.middleware.idempotency import IdempotencyMiddleware
from app.middleware.request_context import RequestContextMiddleware

app = FastAPI(title=settings.service_name, version="0.1.0")
app.add_middleware(RequestContextMiddleware)
if settings.enforce_authentication:
    app.add_middleware(AuthenticationMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
if settings.enforce_idempotency:
    app.add_middleware(IdempotencyMiddleware)


# Exception handlers for proper error responses
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", {}),
    )


app.include_router(router)
