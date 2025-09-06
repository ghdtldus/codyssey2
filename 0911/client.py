import argparse
import socket
import threading
import sys


class ChatClient:
    def __init__(self, host: str, port: int, name: str) -> None:
        self.host = host
        self.port = port
        self.name = name
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._closed = False

    @staticmethod
    def _send_line(sock: socket.socket, text: str) -> None:
        data = (text + '\n').encode('utf-8', errors='ignore')
        sock.sendall(data)

    def _recv_loop(self) -> None:
        # 서버에서 오는 메시지 출력
        file_obj = self.sock.makefile('r', encoding='utf-8', newline='\n')
        try:
            for line in file_obj:
                sys.stdout.write(line)  # 줄 끝에 \n 포함
                sys.stdout.flush()
        except (ConnectionResetError, BrokenPipeError):
            pass
        finally:
            self._closed = True

    def run(self) -> None:
        # 서버 연결 후 송수신 루프
        self.sock.connect((self.host, self.port))

        # 1) 닉네임 전송
        self._send_line(self.sock, self.name)

        # 2) 수신 쓰레드 시작
        t = threading.Thread(target=self._recv_loop, daemon=True)
        t.start()

        # 3) 입력 루프
        try:
            while not self._closed:
                try:
                    text = input().strip()
                except EOFError:
                    text = '/종료'
                if not text:
                    continue
                self._send_line(self.sock, text)
                if text == '/종료':
                    break
        except KeyboardInterrupt:
            self._send_line(self.sock, '/종료')
        finally:
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
