#!/usr/bin/env python3
"""
멀티쓰레드 TCP 소켓 채팅 서버
PEP 8 스타일 가이드를 준수하여 작성
"""

import socket
import threading
import sys


class ChatServer:
    """멀티쓰레드 채팅 서버 클래스"""
    
    def __init__(self, host='localhost', port=8888):
        """서버 초기화"""
        self.host = host
        self.port = port
        self.clients = []
        self.client_names = {}
        self.server_socket = None
        self.running = False
        
    def start_server(self):
        """서버 시작"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            
            print(f'채팅 서버가 {self.host}:{self.port}에서 시작되었습니다.')
            print('클라이언트 연결을 기다리는 중...')
            
            while self.running:
                try:
                    client_socket, client_address = self.server_socket.accept()
                    print(f'새로운 연결: {client_address}')
                    
                    # 새로운 클라이언트를 위한 쓰레드 생성
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, client_address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                except socket.error:
                    if self.running:
                        print('서버 소켓 오류가 발생했습니다.')
                    break
                    
        except Exception as e:
            print(f'서버 시작 중 오류 발생: {e}')
        finally:
            self.stop_server()
    
    def handle_client(self, client_socket, client_address):
        """클라이언트 연결 처리"""
        try:
            # 클라이언트 이름 받기
            name_message = client_socket.recv(1024).decode('utf-8')
            client_name = name_message.strip()
            
            # 클라이언트 정보 저장
            self.clients.append(client_socket)
            self.client_names[client_socket] = client_name
            
            # 입장 메시지 전송
            welcome_message = f'{client_name}님이 입장하셨습니다.'
            self.broadcast_message(welcome_message, client_socket)
            print(f'{client_name}님이 입장했습니다.')
            
            # 클라이언트 메시지 처리
            while self.running:
                try:
                    message = client_socket.recv(1024).decode('utf-8')
                    if not message:
                        break
                        
                    message = message.strip()
                    
                    # 종료 명령어 처리
                    if message == '/종료':
                        self.remove_client(client_socket, client_name)
                        break
                    
                    # 귀속말 처리 (보너스 기능)
                    if message.startswith('/귀속말 '):
                        self.handle_whisper(client_socket, client_name, message)
                        continue
                    
                    # 일반 메시지 브로드캐스트
                    formatted_message = f'{client_name}> {message}'
                    self.broadcast_message(formatted_message, client_socket)
                    
                except socket.error:
                    break
                    
        except Exception as e:
            print(f'클라이언트 처리 중 오류: {e}')
        finally:
            self.remove_client(client_socket, self.client_names.get(client_socket, 'Unknown'))
    
    def broadcast_message(self, message, sender_socket=None):
        """모든 클라이언트에게 메시지 전송"""
        message_to_send = f'{message}\n'
        disconnected_clients = []
        
        for client in self.clients:
            if client != sender_socket:
                try:
                    client.send(message_to_send.encode('utf-8'))
                except socket.error:
                    disconnected_clients.append(client)
        
        # 연결이 끊어진 클라이언트 제거
        for client in disconnected_clients:
            self.remove_client(client, self.client_names.get(client, 'Unknown'))
    
    def handle_whisper(self, sender_socket, sender_name, message):
        """귀속말 처리 (보너스 기능)"""
        try:
            # 메시지 파싱: /귀속말 대상이름 메시지내용
            parts = message.split(' ', 2)
            if len(parts) < 3:
                sender_socket.send('귀속말 형식: /귀속말 대상이름 메시지\n'.encode('utf-8'))
                return
            
            target_name = parts[1]
            whisper_message = parts[2]
            
            # 대상 클라이언트 찾기
            target_socket = None
            for client, name in self.client_names.items():
                if name == target_name:
                    target_socket = client
                    break
            
            if target_socket:
                # 귀속말 전송
                whisper_to_target = f'[귀속말] {sender_name}> {whisper_message}'
                whisper_to_sender = f'[귀속말] {sender_name} -> {target_name}: {whisper_message}'
                
                target_socket.send(f'{whisper_to_target}\n'.encode('utf-8'))
                sender_socket.send(f'{whisper_to_sender}\n'.encode('utf-8'))
            else:
                sender_socket.send(f'{target_name}님을 찾을 수 없습니다.\n'.encode('utf-8'))
                
        except Exception as e:
            sender_socket.send(f'귀속말 전송 중 오류: {e}\n'.encode('utf-8'))
    
    def remove_client(self, client_socket, client_name):
        """클라이언트 제거"""
        try:
            if client_socket in self.clients:
                self.clients.remove(client_socket)
            if client_socket in self.client_names:
                del self.client_names[client_socket]
            
            # 퇴장 메시지 전송
            if client_name != 'Unknown':
                goodbye_message = f'{client_name}님이 퇴장하셨습니다.'
                self.broadcast_message(goodbye_message)
                print(f'{client_name}님이 퇴장했습니다.')
            
            client_socket.close()
            
        except Exception as e:
            print(f'클라이언트 제거 중 오류: {e}')
    
    def stop_server(self):
        """서버 중지"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        
        # 모든 클라이언트 연결 종료
        for client in self.clients:
            try:
                client.close()
            except:
                pass
        
        print('서버가 중지되었습니다.')


def main():
    """메인 함수"""
    try:
        server = ChatServer()
        server.start_server()
    except KeyboardInterrupt:
        print('\n서버를 중지합니다...')
        server.stop_server()
    except Exception as e:
        print(f'예상치 못한 오류: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()