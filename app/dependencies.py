from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database import async_session
from redis import Redis


# Define an asynchronous session dependency factory
async def create_async_database_session() -> AsyncSession:
    """
    Create an asynchronous database session using async_session() and yield it.
    This allows database transactions to be managed within FastAPI route dependencies.
    """
    async with async_session() as session:
        yield session  # Yield the session to make it available for use within dependencies
        await session.commit()  # Commit any changes made within the session


# Define a factory function for creating an AuthService dependency
def get_auth_service(auth_service_instance):
    """
    Create an AuthService dependency that receives an asynchronous database session.
    This allows AuthService to interact with the database within FastAPI route dependencies.
    """

    def auth_service_dependency(session: AsyncSession = Depends(create_async_database_session)):
        # Create an instance of AuthService and inject the database session
        return auth_service_instance(session)

    return auth_service_dependency


def cache():
    """
    Create a Redis connection using settings from the application configuration.
    """
    return Redis(
        host=settings.redis_server,
        port=settings.redis_port,
    )
