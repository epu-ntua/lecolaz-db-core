from fastapi import FastAPI
from app.api.health import router as health_router
from app.api.upload_file import router as upload_router
from app.api.list_files import router as list_files_router
from app.api.download_file import router as download_file_router
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

app.include_router(health_router)
app.include_router(list_files_router)
app.include_router(upload_router)
app.include_router(download_file_router)