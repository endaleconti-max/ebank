from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.infrastructure.db import Base, engine


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title="alias-service", lifespan=lifespan)
app.include_router(router)
