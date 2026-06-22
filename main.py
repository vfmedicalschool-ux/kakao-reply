import imaplib
import email
from email.header import decode_header
import time
import os
import requests

def clean(val):
    return val.strip().strip('"').strip("'").strip()

EMAIL_ADDR       = clean(os.environ.get("EMAIL", ""))
APP_PASSWORD     = clean(os.environ.get("PASSWORD", ""))
KEYWORD          = clean(os.environ.get("KEYWORD", ""))
REPLY_BODY       = os.environ.get("REPLY_BODY", "").strip()
CHECK_INTERVAL   = int(os.environ.get("CHECK_INTERVAL", "300"))
SENDGRID_API_KEY = clean(os.environ.get("SENDGRID_API_KEY", ""))

IMAP_SERVER = "imap.kakao.com"
IMAP_PORT   = 993

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
    response = requests.post(
        "https://api.sendgrid.com/v3/mail/send",
        headers={
            "Authorization": "Bearer " + SENDGRID_API_KEY,
            "Content-Type": "application/json"
        },
        json={
            "personalizations": [{"to": [{"email": to_addr}]}],
            "from": {"email": EMAIL_ADDR},
            "subject": "Re: " + original_subject,
            "content": [{"type": "text/plain", "value": REPLY_BODY}]
        }
    )
    if response.status_code == 202:
        print(f"[OK] 자동 회신 완료 → {to_addr}")
    else:
        print(f"[ERROR] SendGrid: {response.status_code} / {response.text}")

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
            msg       = email.message_from_bytes(raw[0][1])
            subject   = decode_str(msg.get("Subject", ""))
            from_raw  = msg.get("From", "")
            from_addr = extract_addr(from_raw)

            print(f"  제목: {subject}")

            if KEYWORD in subject and EMAIL_ADDR not in from_addr:
                send_reply(from_addr, subject)
                imap.store(uid, "+FLAGS", "\\Seen")

        imap.logout()

    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    print("=== 카카오메일 자동 회신 시작 ===")
    print(f"계정   : {EMAIL_ADDR}")
    print(f"키워드 : {KEYWORD}")
    print(f"주기   : {CHECK_INTERVAL}초마다 확인")
    print(f"API키  : {SENDGRID_API_KEY[:15]}... (길이:{len(SENDGRID_API_KEY)})")
    print("================================")

    while True:
        run_once()
        time.sleep(CHECK_INTERVAL)
