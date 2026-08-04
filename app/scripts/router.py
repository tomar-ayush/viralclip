from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.db import get_async_session
from app.common.security import decrypt_api_key
from app.users.model import User, UserAPIKey, KeyProvider
from app.scripts.schema import ScriptGenerateRequest, ScriptResponse
from app.scripts.service import script_service

router = APIRouter(prefix="/scripts", tags=["Scripts"])


@router.post("/generate", response_model=ScriptResponse, summary="Synthesize timed script schema using OpenAI BYOK key")
async def generate_script(
    request: ScriptGenerateRequest,
    session: AsyncSession = Depends(get_async_session)
):
    user_stmt = select(User).where(User.id == request.user_id)
    user_res = await session.exec(user_stmt)
    if not user_res.first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id '{request.user_id}' not found."
        )

    key_stmt = select(UserAPIKey).where(
        UserAPIKey.user_id == request.user_id,
        UserAPIKey.provider == KeyProvider.OPENAI
    )
    key_res = await session.exec(key_stmt)
    api_key_obj = key_res.first()

    openai_key = "mock_openai_key"
    if api_key_obj:
        try:
            openai_key = decrypt_api_key(api_key_obj.encrypted_key)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed decrypting stored API key: {str(e)}"
            )

    return await script_service.generate_script(
        topic=request.topic,
        tone=request.tone,
        target_duration_seconds=request.target_duration_seconds,
        openai_api_key=openai_key
    )
