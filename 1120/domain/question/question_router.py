from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import Question


# 모든 경로 앞에 /api/question 이 붙음
# tags : Swagger docs 에서 묶음 이름
router = APIRouter(
    prefix='/api/question',
    tags=['question'],
)


# ORM 객체(Question) → dict(JSON으로 반환 가능한 형태)로 바꿔주는 함수
# Pydantic 모델을 사용하지 않고 직접 dict로 만드는 방식
def _question_to_dict(question: Question) -> dict:
    return {
        'id': question.id,
        'subject': question.subject,
        'content': question.content,
        'create_date': question.create_date,
    }


# GET /api/question/
# DB에 저장된 question 목록을 ORM으로 조회해서 반환하는 함수
@router.get('/', name='question_list')
def question_list(db: Session = Depends(get_db)) -> List[dict]:
    # ORM을 이용해 question 테이블의 모든 row 조회
    # order_by(Question.id.asc()) : id 오름차순 정렬
    questions = db.query(Question).order_by(Question.id.asc()).all()

    # 반환할 리스트 생성
    result: List[dict] = []

    # ORM 객체를 dict 형태로 변환
    for question in questions:
        item = _question_to_dict(question)
        result.append(item)

    # 최종적으로 JSON 목록 반환
    return result