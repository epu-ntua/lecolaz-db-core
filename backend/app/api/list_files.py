from fastapi import APIRouter, Query
from storage.postgres import PostgresStore

router = APIRouter()

@router.get("/files")
def list_files(limit: int = Query(100, le=500)):
    pg = PostgresStore()
    files = pg.list_files(limit=limit)
    return files
