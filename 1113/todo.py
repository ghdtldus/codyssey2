from typing import Any, Dict, List
from fastapi import FastAPI, APIRouter, HTTPException, Body
import csv
from pathlib import Path
from datetime import datetime

# 업데이트 모델
from model import TodoItem

# CSV 파일 경로 상수
CSV_PATH = Path('todos.csv')

# 메모리 상의 TODO 리스트
# 예: {'id': 1, 'title': 'buy milk', 'done': False, 'created_at': '2025-11-09T10:00:00'}
todo_list: List[Dict[str, Any]] = []

# FastAPI 애플리케이션과 라우터
app = FastAPI(title='CSV-backed TODO API', version='1.1.0')
router = APIRouter(prefix='/todos', tags=['todos'])


# ----- CSV 유틸 함수들 -----

def ensure_csv_initialized() -> None:
    # CSV 파일이 없으면 헤더를 포함해 생성한다.
    if not CSV_PATH.exists():
        with CSV_PATH.open('w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'title', 'done', 'created_at'])


def load_from_csv() -> List[Dict[str, Any]]:
    # CSV에서 모든 TODO 항목을 읽어 리스트로 반환한다.
    ensure_csv_initialized()
    items: List[Dict[str, Any]] = []
    with CSV_PATH.open('r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            done_value = True if str(row.get('done', '')).lower() == 'true' else False
            items.append({
                'id': int(row['id']),
                'title': row['title'],
                'done': done_value,
                'created_at': row['created_at'],
            })
    return items


def append_to_csv(item: Dict[str, Any]) -> None:
    # 단일 TODO 항목을 CSV에 추가한다.
    ensure_csv_initialized()
    with CSV_PATH.open('a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            item['id'],
            item['title'],
            str(item['done']),
            item['created_at'],
        ])


def write_all_to_csv(items: List[Dict[str, Any]]) -> None:
    # 메모리의 전체 리스트를 CSV에 다시 쓴다(수정/삭제에 사용).
    ensure_csv_initialized()
    with CSV_PATH.open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'title', 'done', 'created_at'])
        for it in items:
            writer.writerow([it['id'], it['title'], str(it['done']), it['created_at']])


def next_id(existing: List[Dict[str, Any]]) -> int:
    # 다음 ID를 계산한다.
    if not existing:
        return 1
    return max(x.get('id', 0) for x in existing) + 1


def find_index_by_id(items: List[Dict[str, Any]], todo_id: int) -> int:
    # 해당 id의 인덱스를 찾는다. 없으면 -1 반환.
    for idx, it in enumerate(items):
        if int(it.get('id', -1)) == int(todo_id):
            return idx
    return -1


# ----- 부트스트랩: 서버 시작 전 CSV → 메모리 적재 -----

@app.on_event('startup')
def on_startup() -> None:
    # 서버 시작 시 CSV 내용을 todo_list에 적재한다.
    global todo_list
    todo_list = load_from_csv()


# ----- 라우트 구현 -----

@router.post('/add')
def add_todo(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    # TODO 항목을 추가한다. 입력/출력은 Dict.
    if not payload or not isinstance(payload, dict) or len(payload.keys()) == 0:
        raise HTTPException(status_code=400, detail='입력 값이 비었습니다. 유효한 Dict를 보내주세요.')

    title = str(payload.get('title', '')).strip()
    done = bool(payload.get('done', False))

    if title == '':
        raise HTTPException(status_code=400, detail='title 필드는 비울 수 없습니다.')

    new_item = {
        'id': next_id(todo_list),
        'title': title,
        'done': done,
        'created_at': datetime.utcnow().isoformat(timespec='seconds'),
    }

    todo_list.append(new_item)
    append_to_csv(new_item)

    return {'message': '추가되었습니다.', 'item': new_item, 'count': len(todo_list)}


@router.get('/list')
def retrieve_todo() -> Dict[str, Any]:
    # TODO 리스트를 Dict로 감싸서 반환한다.
    return {'todos': todo_list, 'count': len(todo_list)}


@router.get('/{todo_id}')
def get_single_todo(todo_id: int) -> Dict[str, Any]:
    # 개별 조회: 경로 매개변수로 id를 받는다.
    idx = find_index_by_id(todo_list, todo_id)
    if idx == -1:
        raise HTTPException(status_code=404, detail='해당 id의 항목을 찾을 수 없습니다.')
    return {'item': todo_list[idx]}


@router.put('/{todo_id}')
def update_todo(todo_id: int, payload: TodoItem) -> Dict[str, Any]:
    # 수정: 경로 매개변수 id + 바디로 TodoItem
    idx = find_index_by_id(todo_list, todo_id)
    if idx == -1:
        raise HTTPException(status_code=404, detail='해당 id의 항목을 찾을 수 없습니다.')

    current = todo_list[idx].copy()

    # 부분 업데이트 가능: None이 아닌 값만 반영
    if payload.title is not None:
        new_title = str(payload.title).strip()
        if new_title == '':
            raise HTTPException(status_code=400, detail='title 필드는 비울 수 없습니다.')
        current['title'] = new_title
    if payload.done is not None:
        current['done'] = bool(payload.done)

    # 업데이트 반영
    todo_list[idx] = current
    write_all_to_csv(todo_list)

    return {'message': '수정되었습니다.', 'item': current}


@router.delete('/{todo_id}')
def delete_single_todo(todo_id: int) -> Dict[str, Any]:
    # 삭제: 경로 매개변수 id
    idx = find_index_by_id(todo_list, todo_id)
    if idx == -1:
        raise HTTPException(status_code=404, detail='해당 id의 항목을 찾을 수 없습니다.')

    removed = todo_list.pop(idx)
    write_all_to_csv(todo_list)

    return {'message': '삭제되었습니다.', 'deleted': removed, 'count': len(todo_list)}


# 라우터 등록
app.include_router(router)
