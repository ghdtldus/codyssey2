#!/usr/bin/env python3
"""
채팅 클라이언트
PEP 8 스타일 가이드를 준수하여 작성
"""

import socket
import threading
import sys


class ChatClient:
    """채팅 클라이언트 클래스"""
    
    def __init__(self, host='localhost', port=8888):
        """클라이언트 초기화"""
        self.host = host
        self.port = port
        self.socket = None
        self.name = ''
        self.running = False
        
    def connect_to_server(self):
        """서버에 연결"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.running = True
            
            # 사용자 이름 입력
            self.name = input('사용자 이름을 입력하세요: ').strip()
            if not self.name:
                self.name = 'Anonymous'
            
            # 서버에 이름 전송
            self.socket.send(self.name.encode('utf-8'))
            
            # 메시지 수신 쓰레드 시작
            receive_thread = threading.Thread(target=self.receive_messages)
            receive_thread.daemon = True
            receive_thread.start()
            
            print(f'{self.name}님, 채팅방에 입장했습니다!')
            print('메시지를 입력하세요. (/종료로 나가기, /귀속말 대상이름 메시지로 귀속말)')
            print('-' * 50)
            
            # 메시지 전송
            self.send_messages()
            
        except ConnectionRefusedError:
            print('서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.')
        except Exception as e:
            print(f'연결 중 오류 발생: {e}')
        finally:
            self.disconnect()
    
    def receive_messages(self):
        """서버로부터 메시지 수신"""
        try:
            while self.running:
                message = self.socket.recv(1024).decode('utf-8')
                if not message:
                    break
                print(message.strip())
        except socket.error:
            if self.running:
                print('서버와의 연결이 끊어졌습니다.')
        except Exception as e:
            print(f'메시지 수신 중 오류: {e}')
    
    def send_messages(self):
        """메시지 전송"""
        try:
            while self.running:
                message = input()
                
                if message.strip() == '/종료':
                    self.socket.send('/종료'.encode('utf-8'))
                    break
                elif message.strip():
                    self.socket.send(message.encode('utf-8'))
                    
        except KeyboardInterrupt:
            print('\n프로그램을 종료합니다...')
            self.socket.send('/종료'.encode('utf-8'))
        except Exception as e:
            print(f'메시지 전송 중 오류: {e}')
    
    def disconnect(self):
        """서버 연결 해제"""
        self.running = False
        if self.socket:
            self.socket.close()
        print('채팅을 종료합니다.')


def main():
    """메인 함수"""
    try:
        client = ChatClient()
        client.connect_to_server()
    except KeyboardInterrupt:
        print('\n프로그램을 종료합니다...')
    except Exception as e:
        print(f'예상치 못한 오류: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()