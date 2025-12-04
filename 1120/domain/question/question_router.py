from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Question


router = APIRouter(
    prefix='/api/question',
    tags=['question'],
)


#  Pydantic 스키마
class QuestionSchema(BaseModel):
    id: int
    subject: str
    content: str
    create_date: datetime

    class Config:
        orm_mode = True


class QuestionCreateSchema(BaseModel):
    subject: str
    content: str


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
@router.post('/', name='create_question', response_model=QuestionSchema)
def create_question(
    payload: QuestionCreateSchema,
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
