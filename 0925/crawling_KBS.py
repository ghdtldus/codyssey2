from typing import Dict, List, Set, Tuple
from urllib.parse import urljoin
from pprint import pprint
import requests
from bs4 import BeautifulSoup


BASE_URL: str = 'https://news.kbs.co.kr'
MAIN_URL: str = 'https://news.kbs.co.kr/news/pc/main/main.html'

# 개발자 도구로 확인한 '고유한 값(선택자)'들.
# (title_selector, link_selector)의 튜플 목록이며, 위에서 아래 순서대로 적용한다.
# - 메인 큰 헤드라인: div.box-head-line p.news-txt / 같은 블록의 a[href*="/news/view.do"]
# - 이슈/카드 리스트: #issue a.box-content 내부의 p.title.normal-weight
# - 작은 서브/더보기 등 보조 섹션들도 포괄적으로 커버
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


def _clean_text(text: str) -> str:
    return ' '.join((text or '').split()).strip()


# 요청 헤더를 세팅하여 HTML을 가져오고 BeautifulSoup으로 파싱한다.
def _fetch_soup(url: str) -> BeautifulSoup:
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        )
    }
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, 'html.parser')

# KBS 메인 페이지에서 가능한 많은 헤드라인(제목/URL)을 수집해 리스트로 반환
def get_kbs_headlines() -> List[Dict[str, str]]:
    soup = _fetch_soup(MAIN_URL)

    results: List[Dict[str, str]] = []
    seen_titles: Set[str] = set()  # 제목 기준 중복 제거(동일 카드가 여러 선택자에 걸릴 수 있음)

    def add_item(title_text: str, href: str) -> None:
        # 제목/링크를 정제하고 중복 없이 결과에 추가한다.
        title = _clean_text(title_text)
        url = urljoin(BASE_URL, href or '')
        if not title or not url:
            return
        if title in seen_titles:
            return
        seen_titles.add(title)
        results.append({'title': title, 'url': url})

    # 각 섹션별로 링크 → 제목 혹은 제목 → 링크 순으로 탐색하여 누락을 줄인다.
    for title_sel, link_sel in HEADLINE_SELECTORS:
        # (A) 링크 목록을 먼저 순회하면서 제목을 근처에서 찾는 방식
        for link in soup.select(link_sel):
            # 1차: 해당 링크 내부에서 'title_sel'의 가장 마지막 토큰(p.title 등)만 시도
            # (몇몇 구조에서 상위/형제에 p.title이 붙는 경우가 있어 보수적으로 접근)
            last_token = title_sel.split()[-1]  # 예: 'p.title.normal-weight'
            title_tag = link.select_one(last_token)

            # 2차: 못 찾으면 자식 쪽에서 널리 쓰이는 후보를 시도
            if not title_tag:
                title_tag = link.select_one('p.title') or link.select_one('p.news-txt')

            if title_tag and link.get('href'):
                add_item(title_tag.get_text(strip=True), link.get('href'))

        # (B) 반대로 제목을 먼저 순회하면서 인접한 링크를 추정하는 방식(보조)
        for title_tag in soup.select(title_sel):
            # 같은 카드 내부 혹은 부모/형제에서 a 태그를 찾는다.
            link_tag = (
                title_tag.find_parent('a') or
                title_tag.find_previous('a') or
                title_tag.find_next('a')
            )
            if link_tag and link_tag.get('href'):
                add_item(title_tag.get_text(strip=True), link_tag.get('href'))

    return results


if __name__ == '__main__':
    headlines = get_kbs_headlines()
    for item in headlines:
        print(item)
