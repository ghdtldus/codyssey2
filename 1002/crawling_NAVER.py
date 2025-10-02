import os
import time
import pickle
from selenium import webdriver  #브라우저 인스턴스를 만들고 제어
from selenium.webdriver.common.by import By #요소를 찾을 때 사용하는 전략(id, class_name, css selector 등)
from selenium.webdriver.chrome.service import Service #Selenium 4 이후 드라이버 경로를 지정할 때 공식적으로 사용하는 방식

# 현재 파이썬 파일이 있는 폴더의 절대 경로
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# ChromeDriver의 위치
DRIVER_PATH = os.path.join(BASE_DIR, '..', 'chromedriver-win64', 'chromedriver.exe')  # <- 핵심
# 저장할 쿠키 파일의 경로
COOKIE_PATH = os.path.join(BASE_DIR, 'naver_cookies.pkl')

def build_driver():
    # 드라이버가 존재하는지 확인
    if not os.path.isfile(DRIVER_PATH):
        raise FileNotFoundError(f'[오류] ChromeDriver 경로가 올바르지 않습니다: {DRIVER_PATH}')

    # ChromeOptions 생성: 브라우저 동작을 제어하는 옵션 객체
    options = webdriver.ChromeOptions()
    # 탐지 회피: Chrome이 띄우는 "자동화된 소프트웨어에 의해 제어되고 있습니다" 같은 표식을 제거하려는 시도
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)

    # 탐지 회피: User-Agent 문자열을 설정하여 셀레니움 기본 UA를 숨김
    options.add_argument(
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/140.0.0.0 Safari/537.36'
    )

    # Service 객체로 드라이버 경로를 전달
    service = Service(executable_path=DRIVER_PATH)
    # 이를 이용해 webdriver.Chrome() 인스턴스를 생성
    driver = webdriver.Chrome(service=service, options=options)

    # 탐지 회피: navigator.webdriver 감춤 시도(undefined로 정의하도록)
    driver.execute_cdp_cmd(
        'Page.addScriptToEvaluateOnNewDocument',
        {'source': "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"}
    )
    return driver


def save_cookies(driver, filepath=COOKIE_PATH):
    # 바이너리 쓰기 모드로 열기
    with open(filepath, 'wb') as file:
        # 현재 드라이버가 가지고 있는 쿠키를 바이트 형태로 직렬화하여 file에 저장
        pickle.dump(driver.get_cookies(), file)


# 저장해 둔 쿠키 파일을 불러와서 브라우저에 하나씩 추가 -> 자동 로그인
def load_cookies(driver, filepath=COOKIE_PATH):
    with open(filepath, 'rb') as file:
        # 파일에 저장된 바이트를 읽어 리스트로 불러오기
        cookies = pickle.load(file)
    for cookie in cookies:
        # (만료 시각) 항목
        if 'expiry' in cookie:
            # 안전하게 int()로 변환
            cookie['expiry'] = int(cookie['expiry'])
        try:
            # 현재 열린 도메인과 쿠키의 도메인이 일치하면 쿠키 추가
            driver.add_cookie(cookie)
        except Exception:
            # 실패는 무시
            pass

# 쿠키가 있으면 불러와서 자동 로그인 시도 , 없으면 수동 로그인 후 쿠키 저장
def ensure_logged_in_with_cookies(driver):
    driver.get('https://nid.naver.com/nidlogin.login')  # 로그인 페이지로 바로 이동
    time.sleep(2) # 페이지가 완전히 로드되기 전에 쿠키 추가나 다른 동작을 하면 오류가 날 수 있으므로 잠깐 대기

    # 경로에 naver_cookies.pkl 파일이 존재하면
    if os.path.exists(COOKIE_PATH):
        with open(COOKIE_PATH, 'rb') as f:
            for c in pickle.load(f):
                if 'expiry' in c:
                    c['expiry'] = int(c['expiry'])
                try:
                    driver.add_cookie(c)
                except Exception:
                    pass
        driver.get('https://www.naver.com')  # 쿠키 적용 후 메인으로
        time.sleep(2)
        return

    print('[안내] 최초 1회 수동 로그인이 필요합니다.')
    input('[대기] 브라우저에서 직접 로그인 완료 후 Enter: ')
    # 로그인 성공했는지 간단 검증(우측 상단 메뉴 존재 여부 등)
    driver.get('https://www.naver.com')
    time.sleep(2)
    # 현재 쿠키 리스트를 저장
    with open(COOKIE_PATH, 'wb') as f:
        pickle.dump(driver.get_cookies(), f)
    print('[INFO] 쿠키 저장 완료. 다음부터 자동 로그인됩니다.')


# 메일 제목을 크롤링해서 리스트로 반환.
def get_mail_titles(driver):
    driver.get('https://mail.naver.com') # 네이버 메일 페이지로 이동
    time.sleep(5)

    titles = []
    try:
        # By.CLASS_NAME으로 mail_title 클래스명을 가진 모든 요소(리스트)를 찾음
        elements = driver.find_elements(By.CLASS_NAME, 'mail_title')
        if not elements:
            # strong.subject 같은 다른 셀렉터로 다시 시도
            elements = driver.find_elements(By.CSS_SELECTOR, 'strong.subject')
        for elem in elements:
            # 찾은 요소들을 순회하면서 공백 제거 
            text = elem.text.strip()
            if text:
                titles.append(text)
    except Exception as exc:
        print('[오류] 메일 제목 수집 중 예외:', exc)

    return titles


def main():
    driver = build_driver()
    try:
        ensure_logged_in_with_cookies(driver)
        mail_titles = get_mail_titles(driver)
        print('\n[메일 제목 리스트 객체 출력]')
        for idx, title in enumerate(mail_titles, start=1):
            print(f'{idx:02d}. {title}')
    finally:
        driver.quit()


if __name__ == '__main__':
    main()
