from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from .databse import get_db
from .security import create_api_key

from pydantic import BaseModel

class APIKeyCreateRequest(BaseModel):
    user_id: str

class APIKeyCreateResponse(BaseModel):
    api_key: str

router = APIRouter(
    prefix="/auth", 
    tags=["Authentication"]
)

@router.post("/keys", response_model=APIKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def generate_new_api_key(
    request_data: APIKeyCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    new_key = await create_api_key(db=db, user_id=request_data.user_id)
    return {"api_key": new_key}
