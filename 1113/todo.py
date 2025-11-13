# todo.py
from typing import Any, Dict, List              # 동적 타입 힌트용. Dict[str, Any] 등으로 사용.
from fastapi import FastAPI, APIRouter, HTTPException, Body
                                               # FastAPI 본체, 라우터, 예외, 바디 파라미터 선언.
import csv                                     # 표준 csv 모듈: 파일에 행 단위로 쓰고 읽는다.
from pathlib import Path                       # 경로 다루기. OS 독립적이고 명시적이라 가독성 좋다.
from datetime import datetime                  # 생성 시각을 ISO 문자열로 남기기 위해 사용.

# 업데이트 모델
from model import TodoItem                     # PUT 요청 검증용 Pydantic 모델을 import 한다.

# CSV 파일 경로 상수
CSV_PATH = Path('todos.csv')                   # 현재 작업 폴더 기준 파일명. 없으면 생성한다.

# 메모리 상의 TODO 리스트
# 예: {'id': 1, 'title': 'buy milk', 'done': False, 'created_at': '2025-11-09T10:00:00'}
todo_list: List[Dict[str, Any]] = []           # 서버가 켜지면 CSV를 읽어서 여기에 적재한다.

# FastAPI 애플리케이션과 라우터
app = FastAPI(title='CSV-backed TODO API', version='1.1.0')    # 문서화 제목/버전.
router = APIRouter(prefix='/todos', tags=['todos'])             # 공통 프리픽스와 태그.

# ----- CSV 유틸 함수들 -----

def ensure_csv_initialized() -> None:
    # CSV 파일이 없으면 헤더를 포함해 생성한다.
    if not CSV_PATH.exists():                                   # 파일 존재 여부 확인.
        with CSV_PATH.open('w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)                              # 행 단위로 쓰는 writer 생성.
            writer.writerow(['id', 'title', 'done', 'created_at'])
                                                                # 첫 줄에 헤더 작성.


def load_from_csv() -> List[Dict[str, Any]]:
    # CSV에서 모든 TODO 항목을 읽어 리스트로 반환한다.
    ensure_csv_initialized()                                    # 없으면 파일/헤더 생성.
    items: List[Dict[str, Any]] = []
    with CSV_PATH.open('r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)                              # 각 행을 dict로 읽어 준다(헤더 키 사용).
        for row in reader:
            done_value = True if str(row.get('done', '')).lower() == 'true' else False
                                                                # 'true'/'false' 문자열을 bool로 복구.
            items.append({
                'id': int(row['id']),                           # CSV는 문자열이라 정수로 변환.
                'title': row['title'],                          # 제목은 문자열 그대로.
                'done': done_value,                             # 변환된 불리언 값.
                'created_at': row['created_at'],                # ISO 문자열 그대로.
            })
    return items                                                # CSV 전체를 메모리 리스트로 반환.


def append_to_csv(item: Dict[str, Any]) -> None:
    # 단일 TODO 항목을 CSV에 추가한다.
    ensure_csv_initialized()
    with CSV_PATH.open('a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            item['id'],                                         # 숫자도 CSV에 쓰면 문자열이 된다.
            item['title'],                                      # 문자열.
            str(item['done']),                                  # 불리언을 'True'/'False'로 저장.
            item['created_at'],                                 # ISO 시각 문자열.
        ])


def write_all_to_csv(items: List[Dict[str, Any]]) -> None:
    # 메모리의 전체 리스트를 CSV에 다시 쓴다(수정/삭제에 사용).
    ensure_csv_initialized()
    with CSV_PATH.open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'title', 'done', 'created_at'])  # 전체 재쓰기이므로 헤더부터 새로 쓴다.
        for it in items:
            writer.writerow([it['id'], it['title'], str(it['done']), it['created_at']])


def next_id(existing: List[Dict[str, Any]]) -> int:
    # 다음 ID를 계산한다.
    if not existing:                                            # 비어 있으면 1부터 시작.
        return 1
    return max(x.get('id', 0) for x in existing) + 1            # 가장 큰 id에 +1.


def find_index_by_id(items: List[Dict[str, Any]], todo_id: int) -> int:
    # 해당 id의 인덱스를 찾는다. 없으면 -1 반환.
    for idx, it in enumerate(items):                            # 선형 탐색.
        if int(it.get('id', -1)) == int(todo_id):
            return idx
    return -1                                                   # 못 찾으면 -1.


# ----- 서버 시작 전 CSV → 메모리 적재 -----

@app.on_event('startup')
def on_startup() -> None:
    # 서버 시작 시 CSV 내용을 todo_list에 적재한다.
    global todo_list
    todo_list = load_from_csv()                                 # 한번 읽어 메모리에 올린다.


# ----- 라우트 구현 -----

@router.post('/add')
def add_todo(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    # TODO 항목을 추가한다. 입력/출력은 Dict.
    if not payload or not isinstance(payload, dict) or len(payload.keys()) == 0:
        # payload가 비었거나 dict가 아니거나 키가 0개면 400.
        raise HTTPException(status_code=400, detail='입력 값이 비었습니다. 유효한 Dict를 보내주세요.')

    title = str(payload.get('title', '')).strip()               # 공백 제거해 유효성 체크.
    done = bool(payload.get('done', False))                     # 없으면 False로 간주.

    if title == '':
        # title을 비우는 건 금지.
        raise HTTPException(status_code=400, detail='title 필드는 비울 수 없습니다.')

    new_item = {
        'id': next_id(todo_list),                               # 다음 id 배정.
        'title': title,
        'done': done,
        'created_at': datetime.utcnow().isoformat(timespec='seconds'),
                                                                # UTC ISO 문자열(초 단위까지).
    }

    todo_list.append(new_item)                                  # 메모리에 추가.
    append_to_csv(new_item)                                     # CSV에도 한 줄 추가.

    return {'message': '추가되었습니다.', 'item': new_item, 'count': len(todo_list)}


@router.get('/list')
def retrieve_todo() -> Dict[str, Any]:
    # TODO 리스트를 Dict로 감싸서 반환한다.
    return {'todos': todo_list, 'count': len(todo_list)}        # 간단한 래핑 응답.


@router.get('/{todo_id}')
def get_single_todo(todo_id: int) -> Dict[str, Any]:
    # 개별 조회: 경로 매개변수로 id를 받는다.
    idx = find_index_by_id(todo_list, todo_id)                  # 인덱스 탐색.
    if idx == -1:
        raise HTTPException(status_code=404, detail='해당 id의 항목을 찾을 수 없습니다.')
    return {'item': todo_list[idx]}                             # 찾은 항목 반환.


@router.put('/{todo_id}')
def update_todo(todo_id: int, payload: TodoItem) -> Dict[str, Any]:
    # 수정: 경로 매개변수 id + 바디로 TodoItem
    idx = find_index_by_id(todo_list, todo_id)
    if idx == -1:
        raise HTTPException(status_code=404, detail='해당 id의 항목을 찾을 수 없습니다.')

    current = todo_list[idx].copy()                             # 원본 보호용 복사.

    # 부분 업데이트 가능: None이 아닌 값만 반영
    if payload.title is not None:                               # title 키가 들어왔을 때만 수정.
        new_title = str(payload.title).strip()
        if new_title == '':
            raise HTTPException(status_code=400, detail='title 필드는 비울 수 없습니다.')
        current['title'] = new_title

    if payload.done is not None:                                # done 키가 들어왔을 때만 수정.
        current['done'] = bool(payload.done)

    # 업데이트 반영
    todo_list[idx] = current                                    # 메모리 반영.
    write_all_to_csv(todo_list)                                 # CSV 전체를 덮어써 일관성 유지.

    return {'message': '수정되었습니다.', 'item': current}


@router.delete('/{todo_id}')
def delete_single_todo(todo_id: int) -> Dict[str, Any]:
    # 삭제: 경로 매개변수 id
    idx = find_index_by_id(todo_list, todo_id)
    if idx == -1:
        raise HTTPException(status_code=404, detail='해당 id의 항목을 찾을 수 없습니다.')

    removed = todo_list.pop(idx)                                # 메모리에서 제거.
    write_all_to_csv(todo_list)                                 # CSV 전체를 덮어써 반영.

    return {'message': '삭제되었습니다.', 'deleted': removed, 'count': len(todo_list)}


# 라우터 등록
app.include_router(router)                                      # 실제 앱에 라우터 부착.
