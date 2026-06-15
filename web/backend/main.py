from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .config import settings
from .database import engine, Base
from .routers import auth, jobs, schedules, accounts, billing, analytics

app = FastAPI(title="Cashroll API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(schedules.router)
app.include_router(accounts.router)
app.include_router(billing.router)
app.include_router(analytics.router)

output_dir = Path(settings.output_dir)
output_dir.mkdir(parents=True, exist_ok=True)
app.mount("/videos", StaticFiles(directory=str(output_dir)), name="videos")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
