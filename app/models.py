from sqlalchemy import Column, String, Boolean, DateTime, func, Integer
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class APIKey(Base):
    __tablename__ = 'api_keys'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False) 
    
    public_id = Column(String, nullable=False, unique=True, index=True)
    hashed_secret = Column(String, nullable=False, unique=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    requests_per_minute_limit = Column(Integer, default=100)

class Log(Base):
    __tablename__ = 'api_logs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp_utc = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    user_id = Column(String, nullable=False, index=True)
    http_method = Column(String(10), nullable=False)
    request_path = Column(String, nullable=False)
    status_code = Column(Integer, nullable=False)
