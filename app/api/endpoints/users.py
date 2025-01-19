from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services import user_service
from app.schemas.user import User, UserUpdate
from app.core.security import get_current_user
from typing import List

router = APIRouter()

@router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.put("/me", response_model=User)
async def update_user_me(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await user_service.update_user(current_user.id, user_data, db)

@router.post("/me/deactivate", response_model=User)
async def deactivate_user_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await user_service.deactivate_user(current_user.id, db)
