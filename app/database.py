from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from app.config import settings


Base = declarative_base()


# engine = create_engine(
#     settings.sync_database_url,
#    echo=settings.db_echo_log,
# )

async_engine = create_async_engine(
    settings.async_database_url,
    echo=settings.db_echo_log,
    future=True,
)

# sync_session = sessionmaker(engine, autocommit=False, autoflush=False)

async_session = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


async def create_db_and_tables() -> None:
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
