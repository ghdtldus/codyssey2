from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from domain.question.question_router import router as question_router

# FastAPI 인스턴스 생성
app = FastAPI()
BASE_DIR = Path(__file__).resolve().parent

@app.get('/')
def read_root() -> FileResponse:
    index_path = BASE_DIR / 'frontend' / 'index.html'
    return FileResponse(index_path)

# /questions 라우트를 앱에 등록.
app.include_router(question_router)
