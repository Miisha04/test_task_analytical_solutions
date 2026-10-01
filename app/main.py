from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.elasticsearch import elasticsearch
from app.routers import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        yield
    finally:
        await elasticsearch.close()

app = FastAPI(
    lifespan=lifespan
)

app.include_router(router)