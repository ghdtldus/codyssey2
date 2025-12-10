from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel,  Field
from sqlalchemy.orm import Session

from database import get_db
from models import Question


router = APIRouter(
    prefix='/api/question',
    tags=['question'],
)


#  질문 응답 스키마
class QuestionSchema(BaseModel):
    id: int
    subject: str
    content: str
    create_date: datetime

    class Config:
        orm_mode = True

# 질문 생성 요청 스키마
class QuestionCreate(BaseModel):
    subject: str= Field(..., min_length=1)
    content: str= Field(..., min_length=1)


#  GET 목록 조회
@router.get('/', name='question_list', response_model=List[QuestionSchema])
def question_list(db: Session = Depends(get_db)) -> List[Question]:
    questions: List[Question] = (
        db.query(Question)
        .order_by(Question.id.asc())
        .all()
    )
    return questions


#  POST 질문 생성
@router.post('/', name='create_question', response_model=QuestionSchema,status_code=status.HTTP_201_CREATED)
def question_create(
    payload: QuestionCreate,
    db: Session = Depends(get_db),
) -> Question:
    # ORM 객체 생성
    question = Question(
        subject=payload.subject,
        content=payload.content,
        create_date=datetime.utcnow(),
    )

    # DB 저장   
    db.add(question)
    db.commit()
    db.refresh(question)
    return question
