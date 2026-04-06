from fastapi import FastAPI

from app.api.routes import router
from app.config import settings
from app.infrastructure.db import Base, engine

app = FastAPI(title=settings.service_name, version="0.1.0")


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


app.include_router(router)
