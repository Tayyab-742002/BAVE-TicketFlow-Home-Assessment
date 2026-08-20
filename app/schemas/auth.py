from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    model_config = {
        "json_schema_extra": {
            "examples": [
                {"email": "customer@example.com", "password": "SecurePass123!", "full_name": "Jordan Lee"}
            ]
        }
    }

    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AccessToken(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    model_config = {"json_schema_extra": {"examples": [{"refresh_token": "eyJhbGciOi..."}]}}

    refresh_token: str
