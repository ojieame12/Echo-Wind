from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.core.security import get_password_hash, verify_password
from app.schemas.user import UserCreate, UserUpdate
from fastapi import HTTPException, status

async def get_user(user_id: str, db: AsyncSession) -> User:
    result = await db.execute(select(User).filter(User.id == user_id))
    return result.scalar_one_or_none()

async def get_user_by_email(email: str, db: AsyncSession) -> User:
    result = await db.execute(select(User).filter(User.email == email))
    return result.scalar_one_or_none()

async def get_user_by_username(username: str, db: AsyncSession) -> User:
    result = await db.execute(select(User).filter(User.username == username))
    return result.scalar_one_or_none()

async def create_user(user_data: UserCreate, db: AsyncSession) -> User:
    # Check if email already exists
    if await get_user_by_email(user_data.email, db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if username already exists
    if await get_user_by_username(user_data.username, db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        username=user_data.username,
        company_name=user_data.company_name,
        hashed_password=hashed_password
    )
    
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def update_user(user_id: str, user_data: UserUpdate, db: AsyncSession) -> User:
    user = await get_user(user_id, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update user fields if provided
    if user_data.email:
        existing_user = await get_user_by_email(user_data.email, db)
        if existing_user and existing_user.id != user_id:
            raise HTTPException(status_code=400, detail="Email already registered")
        user.email = user_data.email
    
    if user_data.username:
        existing_user = await get_user_by_username(user_data.username, db)
        if existing_user and existing_user.id != user_id:
            raise HTTPException(status_code=400, detail="Username already taken")
        user.username = user_data.username
    
    if user_data.company_name is not None:
        user.company_name = user_data.company_name
    
    if user_data.password:
        user.hashed_password = get_password_hash(user_data.password)
    
    await db.commit()
    await db.refresh(user)
    return user

async def authenticate_user(email: str, password: str, db: AsyncSession) -> Optional[User]:
    user = await get_user_by_email(email, db)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

async def deactivate_user(user_id: str, db: AsyncSession) -> User:
    user = await get_user(user_id, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = False
    await db.commit()
    await db.refresh(user)
    return user
