import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.header import decode_header
import os

def clean(val):
    return val.strip().strip('"').strip("'").strip()

EMAIL_ADDR    = clean(os.environ.get("EMAIL", ""))
APP_PASSWORD  = clean(os.environ.get("PASSWORD", ""))
KEYWORD       = clean(os.environ.get("KEYWORD", ""))
REPLY_BODY    = os.environ.get("REPLY_BODY", "").strip()
REPLY_SUBJECT = clean(os.environ.get("REPLY_SUBJECT", ""))

IMAP_SERVER = "imap.kakao.com"
IMAP_PORT   = 993
SMTP_SERVER = "smtp.kakao.com"
SMTP_PORT   = 465

ATTACHMENTS = [
    "27학년도_VF_풀케어반 등록TEST_일반생물학 50문제.pdf",
    "27학년도_VF_풀케어반 등록TEST_일반화학 유기화학 30+10문제.pdf",
    "VF 개별 상담용 인적사항 설문 양식_final.hwp",
    "VF 개별 상담용 인적사항 설문 양식_final.pdf",
]

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

def get_subtype(filename):
    ext = filename.lower().split(".")[-1]
    if ext == "pdf":
        return "pdf"
    elif ext == "hwp":
        return "x-hwp"
    else:
        return "octet-stream"

def send_reply(to_addr, original_subject):
    msg = MIMEMultipart()
    msg["From"]    = EMAIL_ADDR
    msg["To"]      = to_addr
    msg["Subject"] = REPLY_SUBJECT if REPLY_SUBJECT else "Re: " + original_subject
    msg.attach(MIMEText(REPLY_BODY, "plain", "utf-8"))

    for filepath in ATTACHMENTS:
        if os.path.exists(filepath):
            with open(filepath, "rb") as f:
                part = MIMEApplication(f.read(), _subtype=get_subtype(filepath))
                part.add_header(
                    "Content-Disposition",
                    "attachment",
                    filename=("utf-8", "", os.path.basename(filepath))
                )
                msg.attach(part)
            print(f"  첨부 완료: {filepath}")
        else:
            print(f"  [경고] 파일 없음: {filepath}")

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.login(EMAIL_ADDR, APP_PASSWORD)
        smtp.sendmail(EMAIL_ADDR, to_addr, msg.as_string())
    print(f"[OK] 자동 회신 완료 → {to_addr}")

def run():
    print(f"계정   : {EMAIL_ADDR}")
    print(f"키워드 : {KEYWORD}")
    print(f"제목   : {REPLY_SUBJECT}")

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

if __name__ == "__main__":
    run()
