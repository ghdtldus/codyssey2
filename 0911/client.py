import argparse
import socket
import threading
import sys


class ChatClient:
    # 멀티스레드 채팅 서버 클래스
    def __init__(self, host: str, port: int, name: str) -> None:
        self.host = host # 접속할 서버 주소
        self.port = port # 접속할 서버 포트
        self.name = name # 닉네임(첫 줄로 서버에 보냄)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # TCP 소켓 생성
        self._closed = False # 수신 스레드 또는 연결 종료 여부 플래그

    @staticmethod
    def _send_line(sock: socket.socket, text: str) -> None:
        # 한 줄(마지막에 \n 포함)을 UTF-8로 보내기
        data = (text + '\n').encode('utf-8', errors='ignore')  # \n으로 라인 경계를 보장
        sock.sendall(data)  # sendall: 버퍼가 전부 송신될 때까지 블로킹

    def _recv_loop(self) -> None:
        # 서버에서 오는 메시지를 계속 읽어 화면에 출력하는 스레드 루프
        file_obj = self.sock.makefile('r', encoding='utf-8', newline='\n')
        try:
            for line in file_obj: # 서버가 보낸 각 줄
                sys.stdout.write(line)  # 그대로 출력(줄 끝에 \n 포함)
                sys.stdout.flush() # 즉시 화면 반영
        except (ConnectionResetError, BrokenPipeError):
            pass
        finally:
            self._closed = True

    def run(self) -> None:
        # 서버로 TCP 연결
        self.sock.connect((self.host, self.port))

        # 1) 닉네임 전송
        self._send_line(self.sock, self.name)

        # 2) 수신 쓰레드 시작(백그라운드에서 메시지 출력)
        t = threading.Thread(target=self._recv_loop, daemon=True) # daemon=True: 메인 종료 시 함께 종료
        t.start()

        # 3) 키보드 입력을 서버로 전송하는 루프
        try:
            while not self._closed:  # 수신 쪽에서 종료 신호가 오면 루프 탈출
                try:
                    text = input().strip() # 공백 제거
                except EOFError: # Ctrl+Z/Ctrl+D 등 표준입력 종료 → 종료 명령으로 변환
                    text = '/종료'
                if not text: # 빈 줄이면 스킵
                    continue
                self._send_line(self.sock, text) # 서버에 전송(일반/명령 포함)
                if text == '/종료': # 내가 종료를 입력한 경우 루프 종료
                    break
        except KeyboardInterrupt: # 터미널에서 Ctrl+C(클라이언트 강제 종료)
            self._send_line(self.sock, '/종료') # 서버에 종료 알림 보내고
        finally:
            # 소켓 닫기(자원 해제)
            try:
                self.sock.close()
            except OSError:
                pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='채팅 클라이언트')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=5000)
    parser.add_argument('--name', required=True, help='닉네임(공백 불가, 최대 20자)')
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    client = ChatClient(args.host, args.port, args.name)
    client.run()


if __name__ == '__main__':
    main()
