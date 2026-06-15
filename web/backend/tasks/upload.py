import json
import tempfile
import traceback
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .celery_app import celery
from ..config import settings

_engine = create_engine(settings.database_url_sync)
_Session = sessionmaker(bind=_engine)


def _decrypt(encrypted: str) -> str:
    from cryptography.fernet import Fernet
    key = settings.secret_key.encode()[:32].ljust(32, b"0")
    import base64
    fernet_key = base64.urlsafe_b64encode(key)
    return Fernet(fernet_key).decrypt(encrypted.encode()).decode()


@celery.task(name="web.backend.tasks.upload.tiktok", bind=True, queue="uploads")
def task_tiktok_upload(self, video_path: str, account_id: str):
    with _Session() as session:
        from ..models import TikTokAccount
        account = session.get(TikTokAccount, account_id)
        if not account:
            raise ValueError(f"Account {account_id} not found")
        cookies_json = _decrypt(account.cookies_encrypted)

    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        f.write(cookies_json)
        cookie_file = f.name

    try:
        from tiktok_uploader.upload import upload_video
        upload_video(video_path, cookies=cookie_file)
    finally:
        Path(cookie_file).unlink(missing_ok=True)
