import uuid
from typing import List

from sqlalchemy import func
from sqlalchemy.sql.expression import false, true, or_, desc, delete, select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.v1.accounts.models import User
from app.v1.models.models import Model
from app.v1.models.schemas import ModelCreate


class ModelsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_models(
            self,
            page: int = None,
            per_page: int = None,
            include_count: bool = False,
            only_public: bool = False,
            owner_id: uuid.UUID = None,) -> (List[Model], int):
        Q = []

        query = select(Model).options(selectinload(Model.owner))

        if only_public:
            Q.append(Model.private == false())

        if owner_id is not None:
            Q.append(and_(Model.owner_id == owner_id, Model.private == true()))

        if len(Q) > 0:
            query = query.filter(or_(*Q))

        total_count = None
        if include_count:
            count_query = select(func.count().label("total_count")).select_from(query.subquery())
            count_result = await self.session.execute(count_query)
            total_count = count_result.scalar()

        query.order_by(desc(Model.created_at))

        if page is not None and per_page is not None:
            query = query.limit(per_page).offset((page - 1) * per_page)

        result = await self.session.execute(query)

        return result.scalars().all(), total_count

    async def get_model(self, model_id: uuid.UUID) -> Model:
        query = select(Model).filter(Model.id == model_id)
        result = await self.session.execute(query)
        return result.scalar()

    async def get_all_user_models(self, user_id: uuid.UUID) -> List[Model]:
        query = select(Model).filter(Model.owner_id == user_id)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_user_model(self, user_id: uuid.UUID, model_id: uuid.UUID) -> Model:
        query = select(Model).filter(Model.owner_id == user_id, Model.id == model_id)
        result = await self.session.execute(query)
        return result.scalar()

    async def get_model_by_name(self, user_id: uuid.UUID, model_name: str) -> Model:
        query = select(Model).filter(and_(Model.owner_id == user_id, Model.name == model_name))
        result = await self.session.execute(query)
        return result.scalar()

    async def delete_model(self, model_id: uuid.UUID) -> None:
        query = delete(Model).where(Model.id == model_id)
        await self.session.execute(query)

    async def create_model(self, model: ModelCreate, path: str, owner: User) -> Model:
        model_obj = Model(**model.model_dump(), path=path, owner=owner)

        self.session.add(model_obj)
        await self.session.commit()
        await self.session.refresh(model_obj)

        return model_obj
