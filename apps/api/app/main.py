from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from app.commerce.routes import router as commerce_router
from app.config import Settings, get_settings
from app.creators.routes import router as creators_router
from app.finance.routes import router as finance_router
from app.health import HealthChecker, InfrastructureHealthChecker
from app.homolog import router as homolog_router
from app.identity.routes import router as identity_router
from app.interaction.routes import router as interaction_router
from app.learning_paths.routes import router as learning_paths_router
from app.recordings.routes import router as recordings_router
from app.scheduling.routes import router as scheduling_router
from app.security import install_security_middleware

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Fake-Signature"],
    expose_headers=["X-Request-ID"],
    max_age=600,
)
install_security_middleware(app, settings)
app.include_router(identity_router)
app.include_router(creators_router)
app.include_router(scheduling_router)
app.include_router(interaction_router)
app.include_router(homolog_router)
app.include_router(commerce_router)
app.include_router(finance_router)
app.include_router(recordings_router)
app.include_router(learning_paths_router)


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
