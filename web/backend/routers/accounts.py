import base64
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_db
from ..models import User, TikTokAccount
from ..schemas import TikTokAccountCreate, TikTokAccountResponse
from ..auth import get_current_user
from ..config import settings

router = APIRouter(prefix="/accounts", tags=["accounts"])


def _encrypt(text: str) -> str:
    from cryptography.fernet import Fernet
    key = settings.secret_key.encode()[:32].ljust(32, b"0")
    fernet_key = base64.urlsafe_b64encode(key)
    return Fernet(fernet_key).encrypt(text.encode()).decode()


@router.post("/", response_model=TikTokAccountResponse)
async def add_account(
    body: TikTokAccountCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    account = TikTokAccount(
        user_id=user.id,
        label=body.label,
        cookies_encrypted=_encrypt(body.cookies_json),
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


@router.get("/", response_model=list[TikTokAccountResponse])
async def list_accounts(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(TikTokAccount).where(TikTokAccount.user_id == user.id))
    return result.scalars().all()


@router.delete("/{account_id}")
async def delete_account(
    account_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(TikTokAccount).where(TikTokAccount.id == account_id, TikTokAccount.user_id == user.id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    await db.delete(account)
    await db.commit()
    return {"ok": True}
