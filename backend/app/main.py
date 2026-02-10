from fastapi import FastAPI
from app.api import health,files,bim
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="LeColaz Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(files.router)
app.include_router(bim.router)
