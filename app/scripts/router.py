from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.common.db import get_async_session
from app.common.security import decrypt_api_key, get_current_user
from app.scripts.schema import ScriptGenerateRequest, ScriptResponse
from app.scripts.service import script_service
from app.users.model import KeyProvider, User, UserAPIKey

router = APIRouter(prefix="/scripts", tags=["Scripts"])


@router.post(
    "/generate",
    response_model=ScriptResponse,
    summary="Synthesize timed script schema using authenticated user's OpenAI BYOK key",
)
async def generate_script(
    request: ScriptGenerateRequest,
    current_user: User = Depends(get_current_user),  # noqa: B008
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
):
    """
    Generates a timed script using the authenticated user's stored OpenAI BYOK key.
    """
    key_stmt = select(UserAPIKey).where(
        UserAPIKey.user_id == current_user.id,
        UserAPIKey.provider == KeyProvider.OPENAI,
    )
    key_res = await session.exec(key_stmt)
    api_key_obj = key_res.first()

    openai_key = "mock_openai_key"
    if api_key_obj:
        try:
            openai_key = decrypt_api_key(api_key_obj.encrypted_key)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed decrypting stored API key: {e!s}",
            )

    return await script_service.generate_script(
        topic=request.topic,
        tone=request.tone,
        target_duration_seconds=request.target_duration_seconds,
        openai_api_key=openai_key,
    )
