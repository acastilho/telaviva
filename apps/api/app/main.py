from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.creators.routes import router as creators_router
from app.health import HealthChecker, InfrastructureHealthChecker
from app.identity.routes import router as identity_router

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(identity_router)
app.include_router(creators_router)


def get_health_checker(configuration: Settings = Depends(get_settings)) -> HealthChecker:
    return InfrastructureHealthChecker(configuration)


@app.get("/health/live", tags=["health"])
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
async def readiness(checker: HealthChecker = Depends(get_health_checker)) -> dict[str, object]:
    try:
        services = await checker.check()
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Infrastructure dependency unavailable",
        ) from error
    return {"status": "ready", "services": services}
