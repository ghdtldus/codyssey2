from fastapi import FastAPI

from domain.question.question_router import router as question_router

# FastAPI 인스턴스 생성
app = FastAPI()

@app.get('/')
def root() -> dict:
    return {'message': 'Hello, Board API'}

# /questions 라우트를 앱에 등록.
app.include_router(question_router)
