from sqlalchemy import Column, String, DateTime, func, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
import uuid


class Model(Base):
    __tablename__ = "models"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    private = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    path = Column(String, unique=True)
    endpoint = Column(String, nullable=True)
    type = Column(String, nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    owner = relationship("User", back_populates="models")

