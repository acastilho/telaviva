from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_settings()
    yield


app = FastAPI(
    title="Tela Viva API",
    description="Veja. Aprenda. Apoie.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "telaviva-api", "version": "0.1.0"}


@app.get("/api/platform", tags=["platform"])
def platform() -> dict[str, object]:
    return {
        "name": "Tela Viva",
        "slogan": "Veja. Aprenda. Apoie.",
        "roles": ["ADMIN", "CREATOR", "VIEWER"],
        "capabilities": ["live", "learning", "support"],
    }
