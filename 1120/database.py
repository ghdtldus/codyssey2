from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
# DB연결 설정

# 현재 폴더(./)에 있는 app.db 파일을 SQLite DB로 사용
# uvicorn 서버를 실행할 때 생성됨
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


# DB 세션을 열고, 사용이 끝나면 자동으로 닫아주는 context manager
@contextmanager
def db_session() -> Session:
    db: Session = SessionLocal()
    try:
        # 여기서 세션을 호출 측에 넘겨줌
        yield db
    finally:
        # 예외 발생 여부와 관계 없이 항상 close
        db.close()


# FastAPI Depends에서 사용할 의존성 함수
# contextlib 기반 db_session()을 내부에서 사용
# 요청이 끝날 때마다 세션이 자동 종료되도록
def get_db() -> Session:
    with db_session() as db: #db안에서만 db_session()이 유효
        # FastAPI의 Depends는 이 함수가 반환하는 값을
        # 엔드포인트 파라미터로 주입해 준다.
        yield db
