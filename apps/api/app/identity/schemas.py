from pydantic import BaseModel, EmailStr, Field, model_validator

from app.identity.models import Audience, Role


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    audience: Audience = Audience.ADULT
    guardian_email: EmailStr | None = None

    @model_validator(mode="after")
    def validate_guardian(self) -> "RegisterRequest":
        if self.audience is Audience.CHILD and self.guardian_email is None:
            raise ValueError("guardian_email is required for child accounts")
        if self.guardian_email is not None and self.guardian_email == self.email:
            raise ValueError("guardian_email must be different from the account email")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20)


class LogoutRequest(RefreshRequest):
    pass


class PasswordRecoveryRequest(BaseModel):
    email: EmailStr


class PasswordResetRequest(BaseModel):
    token: str = Field(min_length=20)
    new_password: str = Field(min_length=12, max_length=128)


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    role: Role
    audience: Audience


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
