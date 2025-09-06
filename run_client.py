#!/usr/bin/env python3
"""
채팅 클라이언트 실행 스크립트
"""

from chat_client import ChatClient

if __name__ == '__main__':
    client = ChatClient()
    client.connect_to_server()