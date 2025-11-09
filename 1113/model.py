from typing import Optional
from pydantic import BaseModel

class TodoItem(BaseModel):
    # 수정 시 사용할 입력 모델
    # 둘 다 선택값으로 두어 부분 업데이트 가능하게 한다.
    title: Optional[str] = None
    done: Optional[bool] = None

