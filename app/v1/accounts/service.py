import uuid
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.v1.accounts.models import User
from app.v1.accounts.schemas import UserCreate
from app.v1.accounts.utils import get_hashed_password, decode_access_token, verify_password, decode_refresh_token


class AccountsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_users(self) -> List[User]:
        query = select(User)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_user(self, user_id: uuid.UUID) -> User:
        query = select(User).filter(User.id == user_id)
        result = await self.session.execute(query)
        return result.scalar()

    async def get_user_by_username(self, username: str) -> User:
        query = select(User).filter(User.username == username)
        result = await self.session.execute(query)
        return result.scalar()

    async def get_user_by_email(self, email: str) -> User:
        query = select(User).filter(User.email == email)
        result = await self.session.execute(query)
        return result.scalar()

    async def get_current_user(self, token: str) -> User:
        payload = decode_access_token(token)
        user = await self.get_user(uuid.UUID(payload.sub))
        return user

    async def get_current_user_by_refresh_token(self, refresh_token: str) -> User:
        payload = decode_refresh_token(refresh_token)
        user = await self.get_user(uuid.UUID(payload.sub))
        return user

    async def create_user(self, user: UserCreate, file_url: str = '') -> (User, str, str):
        hashed_password = get_hashed_password(user.password)
        user.password = hashed_password

        user_obj = User(**user.model_dump(exclude={'avatar'}), avatar=file_url)

        self.session.add(user_obj)
        await self.session.commit()
        await self.session.refresh(user_obj)

        return user_obj

    async def authenticate_user(self, username_or_email: str, password: str) -> (User, str, str):
        user = await self.get_user_by_username(username_or_email) or await self.get_user_by_email(username_or_email)
        if not user or not verify_password(password, user.password):
            return None
        return user
