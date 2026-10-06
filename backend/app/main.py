from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .db import init_db
from .routers import auth, crwo, chat, chat_ws


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="UberGooranda API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(crwo.router)
app.include_router(chat.router)
app.include_router(chat_ws.router)


@app.get("/api/v1/health")
async def health():
    return {"ok": True}
