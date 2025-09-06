#!/usr/bin/env python3
"""
채팅 서버 실행 스크립트
"""

from chat_server import ChatServer

if __name__ == '__main__':
    server = ChatServer()
    server.start_server()