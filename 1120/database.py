from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 현재 폴더(./)에 있는 app.db 파일을 SQLite DB로 사용
SQLALCHEMY_DATABASE_URL = 'sqlite:///./app.db'



# DB 연결(엔진) 만들
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    # SQLite는 하나의 .db 파일을 여러 프로그램이 읽고 쓰는 방식이기에 보수적
    # SQLite는 같은 스레드에서만 접근을 허용
    # FastAPI는 멀티스레드이기에 제한을 풀어줌 
    connect_args={'check_same_thread': False}
)

# DB 세션(트랜잭션) 만들어줌
SessionLocal = sessionmaker(
    # DB 트랜잭션을 자동으로 commit하지 않음
    autocommit=False,
    # flush(실제 쿼리 반영)를 자동으로 하지 않음
    autoflush=False,
    bind=engine
)

# Base는 모든 ORM 클래스의 부모
# 모든 ORM 모델(Question, Answer)은 이 Base를 상속받아야 ->
# SQLAlchemy가 그 모델을 DB 테이블로 인식하고 -> 
# Alembic이 테이블을 생성함 
Base = declarative_base()


# get_db를 통해 API요청마다 DB 세션 열고, 끝나면 닫는 구조를 제공.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
