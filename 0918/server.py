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

# ----------------------------
# 위치정보 제공자 인터페이스
# ----------------------------
class GeolocationProvider:
    # 위치정보 제공자가 반드시 구현해야 할 메소드
    def get_location(self, ip: str) -> Optional[Dict[str, str]]:
        raise NotImplementedError


class NoopProvider(GeolocationProvider):
    # 아무것도 하지 않는 더미 제공자 (위치조회 끔)
    def get_location(self, ip: str) -> Optional[Dict[str, str]]:
        return None


class IpApiProvider(GeolocationProvider):
    """
    ip-api.com 무료 API를 이용해 IP의 국가/도시 등을 조회
    (API 키 불필요, JSON 응답)
    """
    def get_location(self, ip: str) -> Optional[Dict[str, str]]:
        url = f'http://ip-api.com/json/{ip}?fields=status,country,regionName,city,query'
        try:
            # 요청 헤더에 User-Agent를 넣어 API 호출
            req = Request(url, headers={'User-Agent': 'std-http-server/1.0'})
            with urlopen(req, timeout=GEO_TIMEOUT_SEC) as resp:
                data = json.loads(resp.read().decode('utf-8', errors='ignore'))
            # 조회가 성공하면 필요한 정보만 반환
            if data.get('status') == 'success':
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


def is_private_ip(ip: str) -> bool:
    """
    사설망 / 로컬 IP 여부 확인 함수
    사설망 IP는 위치조회하지 않음
    """
    try:
        addr = ip_address(ip)
    except ValueError:
        return True  # 잘못된 IP 문자열은 그냥 사설로 취급
    private_nets = [
        ip_network('10.0.0.0/8'),
        ip_network('172.16.0.0/12'),
        ip_network('192.168.0.0/16'),
        ip_network('127.0.0.0/8'),
        ip_network('169.254.0.0/16'),   # link-local
        ip_network('::1/128'),
        ip_network('fc00::/7'),
        ip_network('fe80::/10'),
    ]
    return any(addr in net for net in private_nets)


def make_geo_provider(name: str) -> GeolocationProvider:
    """
    설정값에 따라 위치정보 제공자를 반환
    """
    if name == 'ipapi':
        return IpApiProvider()
    return NoopProvider()


# 전역 위치정보 제공자 객체 생성
GEO = make_geo_provider(GEO_PROVIDER)

# ----------------------------
# HTTP 요청 핸들러
# ----------------------------
class SimpleHandler(BaseHTTPRequestHandler):
    server_version = 'SpacePirateHTTP/0.1'  # 서버 버전 문자열

    def do_GET(self) -> None:
        """
        GET 요청이 들어왔을 때 처리
        """
        client_ip = self.client_address[0]  # 클라이언트 IP
        now = datetime.now(timezone.utc).astimezone()  # 현재 시간 (로컬 오프셋 포함 ISO 포맷)

        # 위치 정보 조회 (사설망이 아닐 때만)
        geo_text = ''
        if not is_private_ip(client_ip):
            loc = GEO.get_location(client_ip)
            if loc:
                geo_text = f" | Geo: {loc.get('country','')}, {loc.get('region','')}, {loc.get('city','')}"

        # 서버 콘솔에 로그 출력
        print(f'[{now.isoformat()}] GET {self.path} from {client_ip}{geo_text}', file=sys.stdout, flush=True)

        # 요청 경로가 '/' 또는 '/index.html'이면 index.html 서빙
        if self.path in ('/', '/index.html'):
            self._send_index()
        else:
            self._send_not_found()

    # ---- 보조 메소드 ----
    def _send_index(self) -> None:
        """
        index.html 파일을 읽어서 클라이언트에게 전송
        """
        if not os.path.exists(INDEX_FILE):
            self._send_not_found()
            return

        try:
            with open(INDEX_FILE, 'rb') as f:
                body = f.read()
            self.send_response(200)  # HTTP 200 OK
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)   # 파일 내용 전송
        except Exception as exc:
            self._send_error(500, f'Internal Server Error: {exc}')

    def _send_not_found(self) -> None:
        """
        404 Not Found 응답 전송
        """
        body = b'<h1>404 Not Found</h1>'
        self.send_response(404)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, code: int, message: str) -> None:
        """
        임의의 에러 응답 전송
        """
        body = f'<h1>{code}</h1><p>{message}</p>'.encode('utf-8', errors='ignore')
        self.send_response(code)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        """
        기본 제공되는 noisy 로그를 끔
        (우리가 직접 print로 로그를 찍고 있으므로 불필요)
        """
        return


# ----------------------------
# 멀티스레드 서버 클래스
# ----------------------------
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True  # 각 요청을 데몬 스레드에서 처리


# ----------------------------
# 서버 실행 함수
# ----------------------------
def run(host: str = HOST, port: int = PORT) -> None:
    server_address = (host, port)
    httpd = ThreadedHTTPServer(server_address, SimpleHandler)
    print(f'* Serving {INDEX_FILE} at http://{host}:{port} (Ctrl+C to stop)')
    try:
        httpd.serve_forever()  # 무한 루프 돌며 요청 처리
    except KeyboardInterrupt:
        print('\n* Shutting down...')
    finally:
        httpd.server_close()   # 서버 종료


# 프로그램 진입점
if __name__ == '__main__':
    run()
