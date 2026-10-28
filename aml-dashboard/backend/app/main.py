from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.config import settings
from app.core.state import build_app_state


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.container = build_app_state()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="AML Shield backend — FastAPI + OpenAI STR generation + generic ML stub",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_prefix)
