#!/usr/bin/env python3
"""
자동화된 클라이언트 테스트 스크립트
"""

import socket
import time
import threading


def test_client(client_name, messages):
    """테스트 클라이언트 함수"""
    try:
        # 서버에 연결
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect(('localhost', 8888))
        
        # 이름 전송
        client_socket.send(client_name.encode('utf-8'))
        
        # 메시지 수신 쓰레드
        def receive_messages():
            try:
                while True:
                    message = client_socket.recv(1024).decode('utf-8')
                    if not message:
                        break
                    print(f'[{client_name}] 수신: {message.strip()}')
            except:
                pass
        
        receive_thread = threading.Thread(target=receive_messages)
        receive_thread.daemon = True
        receive_thread.start()
        
        # 메시지 전송
        for message in messages:
            time.sleep(1)  # 메시지 간 간격
            client_socket.send(message.encode('utf-8'))
            print(f'[{client_name}] 전송: {message}')
        
        # 종료
        time.sleep(2)
        client_socket.send('/종료'.encode('utf-8'))
        client_socket.close()
        
    except Exception as e:
        print(f'[{client_name}] 오류: {e}')


def main():
    """메인 테스트 함수"""
    print('채팅 서버 테스트를 시작합니다...')
    
    # 테스트 클라이언트들
    clients = [
        ('Alice', ['안녕하세요!', '오늘 날씨가 좋네요', '/귀속말 Bob 비밀 메시지입니다']),
        ('Bob', ['안녕하세요 Alice님!', '네, 정말 좋은 날씨입니다', 'Alice님에게 귀속말을 보냈습니다']),
        ('Charlie', ['모두 안녕하세요!', '저도 참여해도 될까요?'])
    ]
    
    # 모든 클라이언트를 동시에 실행
    threads = []
    for name, messages in clients:
        thread = threading.Thread(target=test_client, args=(name, messages))
        threads.append(thread)
        thread.start()
    
    # 모든 쓰레드 완료 대기
    for thread in threads:
        thread.join()
    
    print('테스트가 완료되었습니다.')


if __name__ == '__main__':
    main()