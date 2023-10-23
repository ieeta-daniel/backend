import uuid
from typing import List

from sqlalchemy import func
from sqlalchemy.sql.expression import false, true, or_, desc, delete, select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.v1.accounts.models import User
from app.v1.repositories.models import Repository
from app.v1.repositories.schemas import RepositoryCreate


class RepositoriesService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_repositories(
            self,
            page: int = None,
            per_page: int = None,
            include_count: bool = False,
            only_public: bool = False,
            owner_id: uuid.UUID = None,) -> (List[Repository], int):
        Q = []

        query = select(Repository).options(selectinload(Repository.owner))

        if only_public:
            Q.append(Repository.private == false())

        if owner_id is not None:
            Q.append(and_(Repository.owner_id == owner_id, Repository.private == true()))

        if len(Q) > 0:
            query = query.filter(or_(*Q))

        total_count = None
        if include_count:
            count_query = select(func.count().label("total_count")).select_from(query.subquery())
            count_result = await self.session.execute(count_query)
            total_count = count_result.scalar()

        query.order_by(desc(Repository.created_at))

        if page is not None and per_page is not None:
            query = query.limit(per_page).offset((page - 1) * per_page)

        result = await self.session.execute(query)

        return result.scalars().all(), total_count

    async def get_repository(self, repository_id: uuid.UUID) -> Repository:
        query = select(Repository).filter(Repository.id == repository_id)
        result = await self.session.execute(query)
        return result.scalar()

    async def get_all_user_repositories(self, user_id: uuid.UUID) -> List[Repository]:
        query = select(Repository).filter(Repository.owner_id == user_id)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_user_repository(self, user_id: uuid.UUID, repository_id: uuid.UUID) -> Repository:
        query = select(Repository).filter(Repository.owner_id == user_id, Repository.id == repository_id)
        result = await self.session.execute(query)
        return result.scalar()

    async def get_repository_by_name(self, username: str, repository_name: str) -> Repository:
        query = select(Repository).filter(Repository.owner.username == username, Repository.name == repository_name)
        result = await self.session.execute(query)
        return result.scalar()

    async def delete_repository(self, repository_id: uuid.UUID) -> None:
        query = delete(Repository).where(Repository.id == repository_id)
        await self.session.execute(query)

    async def create_repository(self, repository: RepositoryCreate, path: str, owner: User) -> Repository:
        repository_obj = Repository(**repository.model_dump(), path=path, owner=owner)

        self.session.add(repository_obj)
        await self.session.commit()
        await self.session.refresh(repository_obj)

        return repository_obj
