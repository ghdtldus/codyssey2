from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
# DB 테이블 구조 정의(컬럼 + 관계)

class Question(Base):
    # 실제 DB 테이블 이름
    __tablename__ = 'question'
    # 컬럼 id 생성. (정수형, primary key, 검색용 인덱스 생성)
    id = Column(Integer, primary_key=True, index=True)
    subject = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    # 데이터 생성 시 자동으로 현재 UTC 시간을 저장.
    create_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # 1:N 관계 (하나의 질문에 여러 답변)
    answers = relationship('Answer', back_populates='question', cascade='all, delete-orphan')


class Answer(Base):
    __tablename__ = 'answer'

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    create_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    question_id = Column(Integer, ForeignKey('question.id'), nullable=False)

    question = relationship('Question', back_populates='answers')