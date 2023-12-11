from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
import uuid


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String, nullable=False)
    name = Column(String, nullable=False)
    avatar = Column(String)
    github_username = Column(String)
    twitter_username = Column(String)
    homepage_url = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    models = relationship("Model", back_populates="owner", cascade="all, delete-orphan")
    repositories = relationship("Repository", back_populates="owner", cascade="all, delete-orphan")

    def __repr__(self):
        return f"id: {self.id}, username: {self.username}"
