from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.models import User
from app.auth.schemas import UserCreate


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_users(self) -> List[User]:
        query = select(User)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_user(self, user_id: int) -> User:
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

    async def create_user(self, user: UserCreate) -> User:
        user_obj = User(**user.model_dump())
        self.session.add(user_obj)
        await self.session.commit()
        await self.session.refresh(user_obj)
        return user_obj

