import argparse
import csv
import os
import smtplib
import ssl
import sys
from getpass import getpass
from email.message import EmailMessage
from email.utils import formataddr

DEFAULT_SMTP_HOST = 'smtp.gmail.com'
DEFAULT_SMTP_PORT_STARTTLS = 587
DEFAULT_SMTP_PORT_SSL = 465

DEFAULT_SENDER = 'ghdtldus03a@gmail.com'
DEFAULT_CSV_PATH = 'mail_target_list.csv'


def read_csv_targets(csv_path: str) -> list[tuple[str, str]]:
    '''CSV 파일에서 (이름, 이메일) 목록을 읽는다. 첫 줄은 헤더로 가정.'''
    targets: list[tuple[str, str]] = []
    with open(csv_path, 'r', encoding='utf-8', newline='') as fp:
        reader = csv.reader(fp)
        header_skipped = False
        for row in reader:
            if not header_skipped:
                header_skipped = True
                continue
            if not row or len(row) < 2:
                continue
            name = row[0].strip()
            email = row[1].strip()
            if name and email:
                targets.append((name, email))
    return targets


def make_default_html(text_body: str) -> str:
    '''--html-file 미지정 시 텍스트를 안전하게 감싼 간단 HTML.'''
    escaped = (text_body or '').replace('&', '&amp;') \
                               .replace('<', '&lt;') \
                               .replace('>', '&gt;')
    return (
        '<!doctype html>'
        '<html><head><meta charset="utf-8"></head>'
        '<body><pre style="font-family:inherit">'
        f'{escaped}'
        '</pre></body></html>'
    )


def build_message(
    mail_from: str,
    mail_to_addrs: list[tuple[str, str]],
    subject: str,
    text_body: str,
    html_body: str | None
) -> EmailMessage:
    '''텍스트/HTML 멀티파트 EmailMessage 구성.'''
    msg = EmailMessage()
    msg['From'] = mail_from
    msg['To'] = ', '.join(formataddr((n, e)) for n, e in mail_to_addrs)
    msg['Subject'] = subject

    msg.set_content(text_body or '')
    if html_body:
        msg.add_alternative(html_body, subtype='html')
    return msg


def send_via_starttls(
    host: str,
    port: int,
    user: str,
    password: str,
    msg: EmailMessage
) -> None:
    '''587/STARTTLS로 SMTP 전송.'''
    context = ssl.create_default_context()
    with smtplib.SMTP(host, port, timeout=20) as server:
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(user, password)
        server.send_message(msg)


def send_via_ssl(
    host: str,
    port: int,
    user: str,
    password: str,
    msg: EmailMessage
) -> None:
    '''465/SSL로 SMTP 전송.'''
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(host, port, context=context, timeout=20) as server:
        server.ehlo()
        server.login(user, password)
        server.send_message(msg)


def resolve_credentials(mail_from: str) -> tuple[str, str]:
    '''환경변수 또는 안전 입력으로 SMTP 사용자/비밀번호 확보.'''
    user = os.environ.get('GMAIL_USER') or mail_from
    password = os.environ.get('GMAIL_APP_PASS')
    if not password:
        password = getpass('앱 비밀번호(16자리, 공백 없이 입력): ')
    return user, password


def read_file_if_exists(path: str | None) -> str | None:
    '''경로가 주어지면 UTF-8로 읽어 문자열 반환. 없으면 None.'''
    if not path:
        return None
    with open(path, 'r', encoding='utf-8') as fp:
        return fp.read()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='CSV 명단 기반 HTML 이메일 그룹 발송(표준 라이브러리만 사용)'
    )
    parser.add_argument('--from', dest='mail_from', default=DEFAULT_SENDER,
                        help='보내는 사람 이메일(기본: 과제 지정 계정)')
    parser.add_argument('--csv', dest='csv_path', default=DEFAULT_CSV_PATH,
                        help='수신자 CSV 경로 (기본: mail_target_list.csv)')
    parser.add_argument('--subject', required=True, help='메일 제목')
    parser.add_argument('--body', required=True, help='텍스트 본문')
    parser.add_argument('--html-file', dest='html_file', default=None,
                        help='HTML 본문 파일 경로 (선택, 없으면 텍스트를 간단 HTML로 래핑)')
    parser.add_argument('--ssl', action='store_true',
                        help='465(SSL/TLS) 사용. 미지정 시 587(STARTTLS)')
    parser.add_argument('--host', default=DEFAULT_SMTP_HOST,
                        help='SMTP 호스트 (기본: smtp.gmail.com)')
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    user, password = resolve_credentials(args.mail_from)

    try:
        targets = read_csv_targets(args.csv_path)
        if not targets:
            raise ValueError('수신자 목록이 비어 있습니다.')

        html_body = read_file_if_exists(args.html_file) or make_default_html(args.body)

        msg = build_message(
            mail_from=args.mail_from,
            mail_to_addrs=targets,
            subject=args.subject,
            text_body=args.body,
            html_body=html_body
        )

        if args.ssl:
            send_via_ssl(args.host, DEFAULT_SMTP_PORT_SSL, user, password, msg)
        else:
            send_via_starttls(args.host, DEFAULT_SMTP_PORT_STARTTLS, user, password, msg)

        print('메일 전송 완료')
        return 0

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
    except FileNotFoundError as exc:
        print(f'파일 오류: {exc}', file=sys.stderr)
        return 15
    except Exception as exc:
        print(f'알 수 없는 오류: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
