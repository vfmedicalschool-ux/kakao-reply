import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
import time
import os

# ================================================
# 설정값 (Railway 환경변수로 입력)
# ================================================
EMAIL_ADDR   = os.environ.get("EMAIL", "")
APP_PASSWORD = os.environ.get("PASSWORD", "")
KEYWORD      = os.environ.get("KEYWORD", "")
REPLY_BODY   = os.environ.get("REPLY_BODY", "")
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", "300"))  # 기본 5분

IMAP_SERVER = "imap.kakao.com"
IMAP_PORT   = 993
SMTP_SERVER = "smtp.kakao.com"
SMTP_PORT   = 465
# ================================================

def decode_str(s):
    if not s:
        return ""
    parts = decode_header(s)
    result = []
    for part, enc in parts:
        if isinstance(part, bytes):
            result.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            result.append(str(part))
    return "".join(result)

def extract_addr(raw):
    if "<" in raw:
        return raw.split("<")[1].strip().rstrip(">")
    return raw.strip()

def send_reply(to_addr, original_subject):
    msg = MIMEMultipart("alternative")
    msg["From"]    = EMAIL_ADDR
    msg["To"]      = to_addr
    msg["Subject"] = f"Re: {original_subject}"
    msg.attach(MIMEText(REPLY_BODY, "plain", "utf-8"))

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.login(EMAIL_ADDR, APP_PASSWORD)
        smtp.sendmail(EMAIL_ADDR, to_addr, msg.as_string())
    print(f"[OK] 자동 회신 완료 → {to_addr}")

def run_once():
    try:
        imap = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        imap.login(EMAIL_ADDR, APP_PASSWORD)
        imap.select("INBOX")

        _, data = imap.search(None, "UNSEEN")
        ids = data[0].split()
        print(f"[체크] 읽지 않은 메일 {len(ids)}개")

        for uid in ids:
            _, raw = imap.fetch(uid, "(RFC822)")
            msg      = email.message_from_bytes(raw[0][1])
            subject  = decode_str(msg.get("Subject", ""))
            from_raw = msg.get("From", "")
            from_addr = extract_addr(from_raw)

            print(f"  제목: {subject}")

            if KEYWORD in subject and EMAIL_ADDR not in from_addr:
                send_reply(from_addr, subject)
                imap.store(uid, "+FLAGS", "\\Seen")  # 읽음 처리 (중복 방지)

        imap.logout()

    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    print("=== 카카오메일 자동 회신 시작 ===")
    print(f"계정   : {EMAIL_ADDR}")
    print(f"키워드 : {KEYWORD}")
    print(f"주기   : {CHECK_INTERVAL}초마다 확인")
    print("================================")

    while True:
        run_once()
        time.sleep(CHECK_INTERVAL)
