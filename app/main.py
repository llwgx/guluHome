import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.database import async_session, init_db
from app.routes.dashboard import router as dashboard_router
from app.routes.push import router as push_router
from app.services.sensor import backfill_from_messages

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    async with async_session() as db:
        await backfill_from_messages(db)
    yield


app = FastAPI(
    title="OneNet Push Receiver",
    description="接收中国移动 OneNet 平台 HTTP 推送数据并存储至 PostgreSQL",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(push_router)
app.include_router(dashboard_router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}
