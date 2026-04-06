from fastapi import FastAPI

from app.api.routes import router
from app.infrastructure.db import Base, engine

app = FastAPI(title="alias-service")
app.include_router(router)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
