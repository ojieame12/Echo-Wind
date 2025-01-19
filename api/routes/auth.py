from datetime import timedelta, datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from typing import Dict
from sqlalchemy.orm import Session

from api.deps import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, get_db
from models.models import User
from passlib.context import CryptContext

router = APIRouter(tags=["auth"])

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@router.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Dict:
    """Get access token"""
    # For testing, accept any credentials
    if form_data.username and form_data.password:
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": form_data.username},
            expires_delta=access_token_expires
        )
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

@router.post("/create_test_user")
async def create_test_user(
    db: Session = Depends(get_db)
) -> Dict:
    """Create a test user"""
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    # Create test user if it doesn't exist
    email = "test@example.com"
    user = db.query(User).filter_by(email=email).first()
    if not user:
        user = User(
            email=email,
            password_hash=pwd_context.hash("testpassword"),
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
    return {
        "email": user.email,
        "id": user.id
    }
