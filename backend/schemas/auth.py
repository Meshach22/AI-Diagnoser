"""backend/schemas/auth.py

Pydantic schemas for authentication and session management.
"""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserPublic(BaseModel):
    id: int
    email: str
    name: str
    role: str = "user"
    is_admin: bool = False


class LoginRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=1, max_length=128, description="User password")


class LoginResponse(BaseModel):
    token: str = Field(..., description="Opaque session bearer token")
    user: UserPublic
    expires_at: float
    idle_expires_at: float


class RegisterRequest(BaseModel):
    email: str = Field(..., description="User email address")
    name: str = Field(..., min_length=1, max_length=80, description="Full name or display name")
    password: str = Field(..., min_length=12, max_length=128, description="Password (at least 12 characters)")

    class Config:
        extra = "forbid"  # Prevents injection of unauthorized administrative attributes


class UserResponse(BaseModel):
    user: UserPublic
    is_authenticated: bool = True


class AuthStatusResponse(BaseModel):
    signup_allowed: bool
    enforce_api: bool
