import argparse
import os
import smtplib
import ssl
import sys
import mimetypes
from email.message import EmailMessage
from getpass import getpass


DEFAULT_SMTP_HOST = 'smtp.gmail.com'

# 기본 방식 포트 번호 (STARTTLS:평문->TLS 전환)
DEFAULT_SMTP_PORT_STARTTLS = 587
# SSL 방식 포트 번호 (처음부터 암호화된 연결)
DEFAULT_SMTP_PORT_SSL = 465

DEFAULT_SENDER = 'ghdtldus03a@gmail.com'
DEFAULT_RECIPIENT = 'ghdtldus@m365.dongyang.ac.kr'

# EmailMessage 라이브러리를 사용해서 메시지를 구성
def build_message(mail_from: str, mail_to: list[str], subject: str, body: str) -> EmailMessage:
    # 이메일 객체 생성
    msg = EmailMessage()
    # 보내는 사람을 From 헤더에 기록
    msg['From'] = mail_from
    # 수신자 여러 명이면 콤바로 구분해서 To 헤더에 기록
    msg['To'] = ', '.join(mail_to)
    # 제목을 넣으면 라이브러리가 인코딩/헤더 포맷을 적절히 처리해줌
    msg['Subject'] = subject
    # 본문 채우기
    msg.set_content(body)
    return msg

    
# 587/STARTTLS로 SMTP에 접속해 전송한다.
def send_via_starttls(host: str, port: int, user: str, password: str, msg: EmailMessage) -> None:
    # TLS 보안 설정을 담는 SSLContext 생성
    context = ssl.create_default_context()
    # 평문(암호화 전) SMTP 소켓을 연다
    # with 블록을 쓰면 블록 종료 시 자동으로 연결 종료/정리가 보장
    with smtplib.SMTP(host, port, timeout=20) as server:
        # 서버에 EHLO(Extended HELLO)를 보내 기능 목록을 받아옴
        server.ehlo()
        # STARTTLS 명령으로 평문 연결을 TLS(암호화 채널)로 업그레이드
        # 이 순간부터 소켓은 TLS로 암호화되어 자격 증명과 본문이 보호
        server.starttls(context=context)
        # (관례) TLS로 전환하면 서버가 광고하는 기능 목록이 바뀔 수 있으므로
        # 다시 한 번 EHLO하여 암호화 이후 최종 능력치 재협상
        server.ehlo()
        # SMTP 서버에 로그인
        server.login(user, password)
        # 메일 전송
        server.send_message(msg)


# 465/SSL로 SMTP에 접속해 전송한다.
def send_via_ssl(host: str, port: int, user: str, password: str, msg: EmailMessage) -> None:
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(host, port, context=context, timeout=20) as server:
        server.ehlo()
        # SMTP 서버에 로그인
        server.login(user, password)
        # 메일 전송
        server.send_message(msg)

# CLI 인자를 파싱한다.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Gmail SMTP로 이메일 전송 (표준 라이브러리만 사용, 첨부 없음)'
    )
    parser.add_argument('--from', dest='mail_from', default=DEFAULT_SENDER,
                        help='보내는 사람 이메일(기본: 과제 지정 계정)')
    parser.add_argument('--to', nargs='+', default=[DEFAULT_RECIPIENT],
                        help='받는 사람 이메일(여러 명 가능, 기본: 과제 지정 계정)')
    parser.add_argument('--subject', required=True, help='메일 제목')
    parser.add_argument('--body', required=True, help='메일 본문 텍스트')
    parser.add_argument('--ssl', action='store_true',
                        help='465(SSL/TLS) 사용. 미지정 시 587(STARTTLS)')
    parser.add_argument('--host', default=DEFAULT_SMTP_HOST, help='SMTP 호스트 (기본: smtp.gmail.com)')
    return parser.parse_args()


# 자격 증명을 환경변수 또는 안전 입력으로 확보한다.
#  사용자: GMAIL_USER 없으면 mail_from 사용
#  비밀번호: GMAIL_APP_PASS 없으면 getpass()로 입력

def resolve_credentials(mail_from: str) -> tuple[str, str]:
    user = os.environ.get('GMAIL_USER') or mail_from
    password = os.environ.get('GMAIL_APP_PASS')
    if not password:
        password = getpass('앱 비밀번호(16자리, 공백 없이 입력): ')
    return user, password


def main() -> int:
    args = parse_args()
    user, password = resolve_credentials(args.mail_from)

    try:
        msg = build_message(
            mail_from=args.mail_from,
            mail_to=args.to,
            subject=args.subject,
            body=args.body
        )

        if args.ssl:
            send_via_ssl(args.host, DEFAULT_SMTP_PORT_SSL, user, password, msg)
        else:
            send_via_starttls(args.host, DEFAULT_SMTP_PORT_STARTTLS, user, password, msg)

        print('메일 전송 완료')
        return 0

    # 예외 처리
    except smtplib.SMTPAuthenticationError as exc:
        print(f'인증 오류: {exc}', file=sys.stderr)
        return 10
    except smtplib.SMTPConnectError as exc:
        print(f'연결 오류: {exc}', file=sys.stderr)
        return 11
    except smtplib.SMTPServerDisconnected as exc:
        print(f'서버 연결 끊김: {exc}', file=sys.stderr)
        return 12
    except TimeoutError as exc:
        print(f'타임아웃: {exc}', file=sys.stderr)
        return 14
    except Exception as exc:
        print(f'알 수 없는 오류: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
