from http.server import BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from http.server import HTTPServer
from typing import Dict, Optional
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from urllib.error import URLError
from ipaddress import ip_address, ip_network
import json
import os
import sys

# ----------------------------
# 기본 설정
# ----------------------------
HOST = '0.0.0.0'              # 서버가 바인드될 주소 (0.0.0.0 → 모든 네트워크 인터페이스 허용)
PORT = 8080                   # 접속할 포트 번호
INDEX_FILE = 'index.html'     # 기본으로 서빙할 HTML 파일
GEO_PROVIDER = 'ipapi'        # IP 기반 위치정보 제공자 ('ipapi' 또는 'none')
GEO_TIMEOUT_SEC = 2.5         # 위치정보 요청시 타임아웃(초)

# 위치정보 제공자 인터페이스
class GeolocationProvider:
    # 위치정보 제공자가 반드시 구현해야 할 메소드
    def get_location(self, ip: str) -> Optional[Dict[str, str]]:
        raise NotImplementedError

class NoopProvider(GeolocationProvider):
    # (위치조회 끔) 구현체
    def get_location(self, ip: str) -> Optional[Dict[str, str]]:
        return None
    

class IpApiProvider(GeolocationProvider):
    def get_location(self, ip: str) -> Optional[Dict[str, str]]:
			  # ip-api.com이라는 무료 서비스의 엔드포인트.
			  # 매개변수로 받은 접속자의 ip를 넣어 그 IP의 위치정보를 알려주는 API
        url = f'http://ip-api.com/json/{ip}?fields=status,country,regionName,city,query'
        try:
            # HTTP 요청 설정 객체 Request의 기본값은 GET요청
            # url와 서버 이름(최소한의 신원)을 정해서 User-Agent 헤더에 담아서 보냄
					  # HTTP 표준에서 최소한의 신원을 밝혀야 하기 때문
            req = Request(url, headers={'User-Agent': 'test-client'})
            
            # urlopen()이 req를 받아서 네트워크로 HTTP 요청을 날리고, 응답 resp를 가져옴
            with urlopen(req, timeout=GEO_TIMEOUT_SEC) as resp:
		            # resp의 바디를 바이트로 읽어와서 UTF-8 문자열로 바꿈(깨진 바이트 무시)
		            # json 모듈의 loads 함수를 사용해서 JSON 문자열을 딕셔너리로 변환
                data = json.loads(resp.read().decode('utf-8', errors='ignore'))
                
            # data 딕셔너리에서 'status'키 값 확인
            if data.get('status') == 'success':
		            # data 딕셔너리에서 필요한 값으로 위치 정보 딕셔너리를 만들어 반환
                return {
                    'ip': data.get('query') or ip,
                    'country': data.get('country') or '',
                    'region': data.get('regionName') or '',
                    'city': data.get('city') or '',
                }
        except URLError:
            return None
        except Exception:
            return None
        return None


# 로컬/사설망 ip 인가? 
# 공인 IP가 아닌 내부망·루프백·특수망 주소는 위치를 알 수 없기 때문에 조회 X
def is_private_ip(ip: str) -> bool:

    try:
        # 매개변수로 받은 ip문자열을 파싱해서 IPv4Address 또는 IPv6Address 객체로 바꿈
        addr = ip_address(ip)
     # 잘못된 문자열
    except ValueError:
        return True
     # 위치조회 스킵할 ip 모음
    private_nets = [		    
        ip_network('10.0.0.0/8'),       # 사설 IPv4 (회사/학교/가정 LAN)
		ip_network('172.16.0.0/12'),    # 사설 IPv4 (회사/학교/가정 LAN)
		ip_network('192.168.0.0/16'),   # 사설 IPv4 (집 공유기 등)
		ip_network('127.0.0.0/8'),      # 루프백(자기 PC 자신)
		ip_network('169.254.0.0/16'),   # IPv4 링크-로컬
		ip_network('::1/128'),          # IPv6 루프백(자기 PC 자신)
		ip_network('fc00::/7'),         # IPv6 사설 주소 (ULA)
		ip_network('fe80::/10'),        # IPv6 링크-로컬
    ]
    # private_nets안의 각각의 객체 net이
    # 우리가 받은 addr에 어느 하나라도 포함되나요? 
    # true -> 조회 x , false -> o
    return any(addr in net for net in private_nets)


# "ipapi", "none" 문자열을 받아 GeolocationProvider를 상속한 객체를 반환하라는 뜻
def make_geo_provider(name: str) -> GeolocationProvider:
    if name == 'ipapi':
        return IpApiProvider()
    return NoopProvider()


# 전역 위치정보 제공자 객체 생성
GEO = make_geo_provider(GEO_PROVIDER)

# HTTP 요청별로 처리 로직 오버라이딩하기 위해 BaseHTTPRequestHandler 상속 받음
class SimpleHandler(BaseHTTPRequestHandler):
    server_version = 'SpacePirateHTTP/0.1'  # 내 서버가 브라우저한테 응답할 때 보여줄 서버 이름

		# 브라우저로 접속 → index.html을 보여줘야하므로 GET 요청이 들어왔을 때 처리 구현
    def do_GET(self) -> None:
		    # 부모 클래스 덕분에 자동으로 내 서버에 접속한 클라이언트의 IP,PORT 튜플 제공받음
        client_ip = self.client_address[0] 
        now = datetime.now(timezone.utc).astimezone()  # UTC 기준 현재 시각을 시스템 로컬 타임존으로 환
        # 위치 정보 조회
        geo_text = ''
        # False면 
        if not is_private_ip(client_ip):
		        # 실제 조회 호출하고 위치 정보를 가진 dict반환 저장
            loc = GEO.get_location(client_ip)
            # 조회 성공 시 로그 문자열 생성
            if loc:
                geo_text = f" | Geo: {loc.get('country','')}, {loc.get('region','')}, {loc.get('city','')}"

        # 서버 콘솔에 로그 출력
        print(f'[{now.isoformat()}] GET {self.path} from {client_ip}{geo_text}', file=sys.stdout, flush=True)

        # 요청 경로가 '/' 또는 '/index.html'이면 index.html 서빙
        if self.path in ('/', '/index.html'):
            self._send_index()
        else:
            self._send_not_found()

    # 모두 공통 패턴(HTTP 응답 전송)

    # index.html 파일을 읽어서 클라이언트에게 전송하는 정상 응답 전송
    def _send_index(self) -> None:
        if not os.path.exists(INDEX_FILE):
            self._send_not_found()
            return

        try:
            with open(INDEX_FILE, 'rb') as f:
                body = f.read()
            self.send_response(200)  # 상태 코드 전송
            self.send_header('Content-Type', 'text/html; charset=utf-8') # 헤더 전송
            self.send_header('Content-Length', str(len(body))) # 헤더 전송
            self.end_headers()  # 헤더 전송
            self.wfile.write(body)   # 바디 전송
        except Exception as exc:
            self._send_error(500, f'Internal Server Error: {exc}')

		# 404 Not Found 응답 전송
    def _send_not_found(self) -> None:
        body = b'<h1>404 Not Found</h1>'
        self.send_response(404) # 상태 코드 전송
        self.send_header('Content-Type', 'text/html; charset=utf-8') # 헤더 전송
        self.send_header('Content-Length', str(len(body))) # 헤더 전송
        self.end_headers() # 헤더 전송
        self.wfile.write(body) # 바디 전송

		# 인자로 받은 에러 응답 전송
    def _send_error(self, code: int, message: str) -> None:
        body = f'<h1>{code}</h1><p>{message}</p>'.encode('utf-8', errors='ignore')
        self.send_response(code) # 인자로 받은 코드 그대로 응답
        self.send_header('Content-Type', 'text/html; charset=utf-8') # 헤더 전송
        self.send_header('Content-Length', str(len(body))) # 헤더 전송
        self.end_headers() # 헤더 전송
        self.wfile.write(body) # 바디 전송

    def log_message(self, format: str, *args) -> None:
        # BaseHTTPRequestHandler에 기본 제공되는 로그를 끔(우리가 직접 print로 로그를 찍을 것이므로 불필요)
        return


# 멀티스레드 서버 클래스
# ThreadingMixIn을 섞으면 요청마다 새 스레드를 만들어 동시에 처리
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True  # ThreadingMixIn이 읽는 설정 플래그. True면 생성되는 작업 스레드들을 데몬 스레드로 만듦


# 서버 실행 함수
def run(host: str = HOST, port: int = PORT) -> None:
		# 서버가 바인드할 주소 튜플(현재 '0.0.0.0', 8080)
    server_address = (host, port)
    
    # 서버 인스턴스 생성(바인드할 주소/포트 , 요청이 들어올 때마다 생성될 핸들러 클래스)
    httpd = ThreadedHTTPServer(server_address, SimpleHandler)
    # 아내 메세지
    print(f'* Serving {INDEX_FILE} at http://{host}:{port} (Ctrl+C to stop)')
    # 메인 이벤트 루프 시
    try:
        httpd.serve_forever()  # 무한 루프 돌며 요청 처리
    except KeyboardInterrupt: # Ctrl+C들어오면 여기로 들어오고 finally로 넘어
        print('\n* Shutting down...')
    finally:
        httpd.server_close()   # 서버 종료

if __name__ == '__main__':
    run()
