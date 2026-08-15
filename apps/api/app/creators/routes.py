from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.config import Settings, get_settings
from app.creators.models import CreatorProfile
from app.creators.repository import (
    CreatorRepository,
    PostgresCreatorRepository,
    UnknownCategoryError,
)
from app.creators.schemas import CategoryResponse, CreatorProfileResponse, CreatorProfileUpdate
from app.identity.models import Role, User
from app.identity.routes import require_roles

router = APIRouter(tags=["creators"])


def get_creator_repository(settings: Settings = Depends(get_settings)) -> CreatorRepository:
    return PostgresCreatorRepository(settings)


def _response(profile: CreatorProfile) -> CreatorProfileResponse:
    return CreatorProfileResponse.model_validate(profile, from_attributes=True)


@router.get("/categories", response_model=list[CategoryResponse])
async def categories(
    repository: CreatorRepository = Depends(get_creator_repository),
) -> list[CategoryResponse]:
    return [
        CategoryResponse.model_validate(item, from_attributes=True)
        for item in await repository.list_categories()
    ]


@router.get("/creators/{user_id}", response_model=CreatorProfileResponse)
async def creator_profile(
    user_id: UUID, repository: CreatorRepository = Depends(get_creator_repository)
) -> CreatorProfileResponse:
    profile = await repository.get_profile(user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Creator profile not found")
    return _response(profile)


@router.put("/creators/me", response_model=CreatorProfileResponse)
async def update_creator_profile(
    body: CreatorProfileUpdate,
    repository: CreatorRepository = Depends(get_creator_repository),
    user: User = require_roles(Role.CREATOR),  # type: ignore[assignment]
) -> CreatorProfileResponse:
    try:
        profile = await repository.upsert_profile(
            user.id,
            photo_url=str(body.photo_url) if body.photo_url else None,
            name=body.name,
            bio=body.bio,
            profession=body.profession,
            specialties=body.specialties,
            tools=body.tools,
            languages=body.languages,
            category_ids=body.category_ids,
            social_links={key: str(value) for key, value in body.social_links.items()},
            default_price=body.default_price,
            accepts_tips=body.accepts_tips,
        )
    except UnknownCategoryError as error:
        raise HTTPException(
            status_code=422, detail="One or more categories do not exist"
        ) from error
    return _response(profile)
