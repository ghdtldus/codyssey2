import argparse
import socket
import threading
from typing import Dict, Optional


class ChatServer:
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        # 수신용 리스닝 소켓
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind((self.host, self.port))
        self.server_sock.listen()

        # 연결 관리
        self._lock = threading.Lock()
        # 닉네임 → 소켓
        self._sock_by_name: Dict[str, socket.socket] = {}
        # 소켓 → 닉네임
        self._name_by_sock: Dict[socket.socket, str] = {}

    # ---------- 네트워크 유틸 ----------

    @staticmethod
    def _send_line(sock: socket.socket, text: str) -> None:
        data = (text + '\n').encode('utf-8', errors='ignore')  # \n으로 라인 경계를 보장
        sock.sendall(data) # sendall: 버퍼가 전부 송신될 때까지 블로킹

    @staticmethod
    def _recv_line(file_obj) -> Optional[str]:
        # 파일 객체에서 한 줄 수신(없으면 None). socket.makefile()로 생성된 객체 사용
        line = file_obj.readline() # \n까지 읽음. 연결 종료 시 ''(빈 문자열) 반환
        if not line:
            return None    # 빈 문자열이면 연결이 끊겼다고 판단
        return line.rstrip('\n') # 오른쪽 끝의 \n 제거(메시지 본문만 사용)

    # ---------- 방송/귓속말 ----------

    def _broadcast(self, text: str, exclude: Optional[socket.socket] = None) -> None:
        # 모든 접속자에게 전송. exclude가 있으면 그 소켓은 제외.
        with self._lock:
            sockets = list(self._sock_by_name.values())

        for sock in sockets: # 현재 접속 중인 모든 소켓에 대해
            if sock is exclude: # 보낸 사람 본인은 제외
                continue
            try:
                self._send_line(sock, text) # 실제 송신
            except OSError:
                # 송신 실패 소켓은 정리
                self._cleanup_socket(sock)

    def _whisper(self, to_name: str, text: str, sender: str) -> bool:
        # 특정 사용자에게 귓속말. 성공 시 True.
        with self._lock:
            target = self._sock_by_name.get(to_name) # 닉네임으로 대상 소켓 조회

        if target is None: # 대상 닉네임이 없으면 실패
            return False

        try:
            self._send_line(target, f'(귓속말){sender}> {text}')  # 수신자에게 귓속말 포맷으로 전송
            return True
        except OSError:
            self._cleanup_socket(target) # 송신 실패 시 정리
            return False

    # ---------- 클라이언트 처리 ----------

    def _cleanup_socket(self, sock: socket.socket) -> None:
        # 소켓 연결 정리 및 사용자 목록에서 제거
        with self._lock:
            name = self._name_by_sock.pop(sock, None) # 소켓→닉네임 맵에서 제거
            if name:
                self._sock_by_name.pop(name, None) # 닉네임→소켓 맵에서도 제거
        try:
            sock.close() # OS 리소스 해제
        except OSError: 
            pass # 이미 닫혔거나 에러 무시

    def _register_name(self, sock: socket.socket, name: str) -> bool:
        # 닉네임 등록. 중복이면 False
        if not name or ' ' in name or len(name) > 20: # 빈 문자열/공백 포함/너무 김 → 불가
            return False
        with self._lock:
            if name in self._sock_by_name:  # 중복 닉네임 방지
                return False
            self._sock_by_name[name] = sock # 닉네임→소켓
            self._name_by_sock[sock] = name # 소켓→닉네임
        return True

    def _handle_client(self, sock: socket.socket, addr) -> None:
        # 각 클라이언트별 쓰레드 엔트리
        reader = sock.makefile('r', encoding='utf-8', newline='\n')

        # 1) 첫 줄은 닉네임
        name = self._recv_line(reader)
        if name is None or not self._register_name(sock, name): # 등록 실패(중복/형식 위반 등)
            try:
                self._send_line(sock, 'ERROR 닉네임이 중복되었거나 사용할 수 없습니다.')
            except OSError:
                pass
            self._cleanup_socket(sock) # 소켓 정리
            return

        # 입장 알림
        join_msg = f'{name}님이 입장하셨습니다.'
        self._broadcast(join_msg)
        try:
            self._send_line(sock, '안내: "/종료"로 종료, "/w 대상닉 메시지"는 귓속말입니다.')
        except OSError:
            self._cleanup_socket(sock)
            return

        # 2) 메시지 루프
        try:
            while True:
                line = self._recv_line(reader) # 라인 단위 수신
                if line is None:
                    break  # 연결 종료

                if line == '/종료': # 정상 종료 명령
                    break

                if line.startswith('/w '): # 귓속말 명령 처리
                    # 형식: /w 대상닉 메시지→ 3파트로 분할
                    parts = line.split(' ', 2)
                    if len(parts) < 3: # 메시지 빠진 경우 사용법 안내
                        self._send_line(sock, '안내: 사용법 -> /w 대상닉 메시지')
                        continue
                    _, to_name, message = parts
                    if not self._whisper(to_name, message, name):  # 귓속말 시도
                        self._send_line(sock, f'안내: "{to_name}" 사용자를 찾을 수 없습니다.')
                    continue

                # # 일반 메시지: 보낸 본인(exclude) 제외하고 모두에게 브로드캐스트
                self._broadcast(f'{name}> {line}', exclude=sock)
        except (ConnectionResetError, BrokenPipeError):
            # 상대가 비정상 종료(연결 리셋 등)해도 서버는 조용히 정리
            pass
        finally:
            # 퇴장 처리
            self._cleanup_socket(sock)
            self._broadcast(f'{name}님이 퇴장하셨습니다.')

    # ---------- 서버 구동 ----------

    def serve_forever(self) -> None:
        # 클라이언트 접속을 accept하고, 접속마다 스레드를 생성
        print(f'[서버] {self.host}:{self.port} 에서 대기 중...')
        try:
            while True:
                # 새 연결 수락(클라이언트의 TCP 3-way handshake 완료된 소켓이 반환)
                client_sock, addr = self.server_sock.accept()
                # 각 연결을 전담할 데몬 스레드 생성(메인 종료 시 함께 정리)
                t = threading.Thread(
                    target=self._handle_client, args=(client_sock, addr), daemon=True
                )
                t.start()
        except KeyboardInterrupt:
            # 터미널에서 Ctrl+C 누르면 여기로 들어옴
            print('\n[서버] 종료합니다.')
        finally:
            # 남은 연결 정리
            with self._lock:
                sockets = list(self._sock_by_name.values())
            for s in sockets:
                self._cleanup_socket(s)
            # 리스닝 소켓 닫기(포트 반환)    
            try:
                self.server_sock.close()
            except OSError:
                pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='멀티스레드 채팅 서버')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=5000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    server = ChatServer(args.host, args.port)
    server.serve_forever()


if __name__ == '__main__':
    main()
