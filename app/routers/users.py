from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import UserRegister, UserLogin, UserOut, Token, UserProfileUpdate
from app.auth import hash_password, verify_password, create_access_token, get_current_user


router = APIRouter(prefix="/api/users", tags=["Authentication & Users"])

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register_user(user_data: UserRegister, response: Response, db: Session = Depends(get_db)):
    """Registers a new user and returns a signed JWT token."""
    existing_user = db.query(User).filter(User.email == user_data.email.lower()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists"
        )

    new_user = User(
        name=user_data.name.strip(),
        email=user_data.email.lower().strip(),
        password_hash=hash_password(user_data.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token({"sub": str(new_user.user_id), "email": new_user.email})

    # Set cookie for browser session convenience
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=86400,
        samesite="lax"
    )

    return Token(
        access_token=token,
        token_type="bearer",
        user=UserOut.model_validate(new_user)
    )

@router.post("/login", response_model=Token)
def login_user(login_data: UserLogin, response: Response, db: Session = Depends(get_db)):
    """Authenticates user credentials and issues a JWT token."""
    user = db.query(User).filter(User.email == login_data.email.lower().strip()).first()
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    token = create_access_token({"sub": str(user.user_id), "email": user.email})

    # Set cookie for browser session convenience
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=86400,
        samesite="lax"
    )

    return Token(
        access_token=token,
        token_type="bearer",
        user=UserOut.model_validate(user)
    )

@router.get("/me", response_model=UserOut)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Returns the authenticated user profile."""
    return UserOut.model_validate(current_user)

@router.put("/me", response_model=UserOut)
@router.put("/profile", response_model=UserOut)
def update_current_user_profile(
    update_data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates permitted profile fields for the authenticated user."""
    if update_data.name is not None and update_data.name.strip():
        current_user.name = update_data.name.strip()

    if update_data.email is not None and update_data.email.lower().strip() != current_user.email:
        new_email = update_data.email.lower().strip()
        existing = db.query(User).filter(User.email == new_email, User.user_id != current_user.user_id).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email address already exists"
            )
        current_user.email = new_email

    if update_data.new_password is not None and update_data.new_password.strip():
        if not update_data.current_password or not verify_password(update_data.current_password, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        current_user.password_hash = hash_password(update_data.new_password)

    db.commit()
    db.refresh(current_user)
    return UserOut.model_validate(current_user)

@router.post("/logout")
def logout_user(response: Response):
    """Clears the access token cookie."""
    response.delete_cookie(key="access_token")
    return {"message": "Logged out successfully"}

