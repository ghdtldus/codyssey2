from typing import Dict, List, Set, Tuple
from urllib.parse import urljoin
from pprint import pprint
import requests
from bs4 import BeautifulSoup


BASE_URL: str = 'https://news.kbs.co.kr'
MAIN_URL: str = 'https://news.kbs.co.kr/news/pc/main/main.html'

# 개발자 도구로 확인한 '고유한 값(선택자)'
# (title_selector, link_selector)의 튜플 목록이며, 위에서 아래 순서대로 적용
HEADLINE_SELECTORS: List[Tuple[str, str]] = [
    # 1) 메인 큰 헤드라인 (제목/링크가 다른 노드에 있을 수 있어 함께 지정)
    ('div.box-head-line p.news-txt', 'div.box-head-line a[href*="/news/view.do"]'),

    # 2) 이슈/카드 리스트 (카드 전체가 링크, 제목은 내부 p.title.normal-weight)
    ('#issue a.box-content p.title.normal-weight', '#issue a.box-content'),

    # 3) 작은 서브 뉴스 묶음 (예: 작은 카드 영역)
    ('div.small-sub-news-wrapper a.box-content p.title.normal-weight',
     'div.small-sub-news-wrapper a.box-content'),

    # 4) 더보기/기타 카드 영역
    ('div.look-more-wrapper a.box-content p.title.normal-weight',
     'div.look-more-wrapper a.box-content'),

    # 5) 안전망: 사이트 전역의 카드 제목 포괄(너무 광범위하면 중복 필터로 정리)
    ('a.box-content p.title', 'a.box-content[href*="/news/view.do"]'),
]



# 공백 문자 제거 후 문자열만 리스트에 저장
def _clean_text(text: str) -> str:
    # 공백 기준으로 쪼개고, 다시 한 칸짜리 공백으로 연결, 맨 앞/뒤 공백 제거
    return ' '.join((text or '').split()).strip()



# URL → BeautifulSoup 객체 변환기
def _fetch_soup(url: str) -> BeautifulSoup:
    # HTTP 요청에 같이 보낼 헤더 정보를 담은 딕셔너리
    headers = {
        # 서버에 '나는 누구다' 라고 보낼 값.
        # 크롤링 할거니까 실제 브라우저 처럼 보이게끔 UA넣을거임.
        # 너무 쉽게 하면 봇이라고 간주당함.
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        )
    }
    # HTTP GET 요청을 보내고 응답을 resp에 담음
    resp = requests.get(url, headers=headers, timeout=10) # 서버 응답이 10초 안에 없으면 에러 발생(무한 대기 방지)
    # resp의 상태 코드가 200이 아니면 에러 내서 멈추게 함
    resp.raise_for_status()
    # 응답 본문을 문자열로 꺼내고,파이썬 내장 HTML 파서 사용하여 객체 생성
    return BeautifulSoup(resp.text, 'html.parser')



# KBS 메인 페이지에서 가능한 많은 헤드라인(제목/URL)을 수집해 리스트로 반환
def get_kbs_headlines() -> List[Dict[str, str]]:
    # 방금 만든 헬퍼로 bs객체 얻음
    soup = _fetch_soup(MAIN_URL)
    # 최종 결과를 담을 리스트
    results: List[Dict[str, str]] = []
    # 제목 기준 중복 제거(동일 카드가 여러 선택자에 걸릴 수 있음)
    seen_titles: Set[str] = set()  

    # 제목/링크를 정제하고 중복 없이 결과에 추가
    def add_item(title_text: str, href: str) -> None:
        # 헬퍼 사용
        title = _clean_text(title_text)
        # 상대경로 href 를 절대 URL 로 바꿈
        url = urljoin(BASE_URL, href or '')

        # 없으면 스킵
        if not title or not url:
            return
        # 이미 본 제목이면 스킵
        if title in seen_titles:
            return
        # 중복 집합에 등록하고, 결과 리스트에 dict로 추가
        seen_titles.add(title)
        results.append({'title': title, 'url': url})

    # 각 섹션별로 링크 → 제목 혹은 제목 → 링크 순으로 탐색하여 누락을 줄인다.
    for title_sel, link_sel in HEADLINE_SELECTORS:
        # (A) 링크 목록을 먼저 순회하면서 제목을 찾는 방식
        # CSS 선택자로 링크 후보를 모두 찾음
        for link in soup.select(link_sel):
            # title_sel 전체를 쓰면 컨텍스트가 달라 빗나갈 수 있어, 가장 마지막 토큰만 탐색
            # (몇몇 구조에서 상위/형제에 p.title이 붙는 경우가 있어 보수적으로 접근)
            last_token = title_sel.split()[-1]  # 예: 'p.title.normal-weight'
            # select_one은 첫 번째 일치 요소만 반환
            title_tag = link.select_one(last_token)

            # 못 찾았으면 대체 후보(흔한 제목 태그)로 한 번 더 시도.
            if not title_tag:
                title_tag = link.select_one('p.title') or link.select_one('p.news-txt')

            if title_tag and link.get('href'):
                add_item(title_tag.get_text(strip=True), link.get('href'))

        # (B) 반대로 제목을 먼저 순회하면서 인접한 링크를 추정하는 방식(보조)
        for title_tag in soup.select(title_sel):
            # 같은 카드 내부 혹은 부모/형제에서 a 태그를 찾는다.
            link_tag = (
                # 부모 방향으로 가장 가까운 <a>
                title_tag.find_parent('a') or
                # 이전 형제/조상 방향
                title_tag.find_previous('a') or
                # 다음 형제/자손 방향
                title_tag.find_next('a')
            )
            if link_tag and link_tag.get('href'):
                add_item(title_tag.get_text(strip=True), link_tag.get('href'))

    return results



if __name__ == '__main__':
    headlines = get_kbs_headlines()
    for item in headlines:
        print(item)
