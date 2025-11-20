from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Question

# 라우터 정의 : 모든 경로가 /questions로 시작.
router = APIRouter(
    prefix='/questions',
    tags=['questions'],
)

# POST 요청에 필요한 값
class QuestionCreate(BaseModel):
    subject: str
    content: str

# ORM 객체를 JSON 응답으로 변환해주는 설정
class QuestionResponse(BaseModel):
    id: int
    subject: str
    content: str
    create_date: datetime

    class Config:
        orm_mode = True

# POST /questions — 데이터 저장
@router.post(
    '/',
    response_model=QuestionResponse,
    status_code=status.HTTP_201_CREATED
)
def create_question(
    payload: QuestionCreate,
    db: Session = Depends(get_db),
) -> Question:
    question = Question(
        subject=payload.subject,
        content=payload.content,
        create_date=datetime.utcnow(),
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


# GET /questions — 전체 목록 조회
@router.get('/', response_model=List[QuestionResponse])
def list_questions(
    db: Session = Depends(get_db),
) -> list[Question]:
    # 역순 조회 ( 게시판 특:신규 글을 위로 )
    questions = db.query(Question).order_by(Question.id.desc()).all()
    return questions

# GET /questions/{id} — 단일 조회
@router.get('/{question_id}', response_model=QuestionResponse)
def get_question(
    question_id: int,
    db: Session = Depends(get_db),
) -> Question:
    question = db.query(Question).filter(Question.id == question_id).first()
    if question is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Question not found',
        )
    return question
