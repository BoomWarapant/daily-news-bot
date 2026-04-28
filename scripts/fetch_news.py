import os
from datetime import datetime
from pathlib import Path
import anthropic
import requests

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"].strip()
LINE_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"].strip()
LINE_USER_ID = os.environ["LINE_USER_ID"].strip()
GITHUB_REPO = os.environ.get("GITHUB_REPOSITORY", "")

NEWS_PROMPT = """สรุปข่าวสำคัญประจำวันของวันนี้ (ภาษาไทย) แบ่งเป็น 4 หมวด:

## ตลาดหุ้นไทย
- SET Index ปิดที่เท่าไหร่ +/- กี่จุด
- CRD.BK ราคาและความเคลื่อนไหว
- หุ้นกลุ่มก่อสร้างเด่นๆ

## ทอง + Bitcoin
- ราคาทองคำ (สมาคมค้าทอง)
- Bitcoin USD

## ข่าวก่อสร้างไทย
- โครงการรัฐ/เอกชนใหม่
- ราคาวัสดุก่อสร้าง
- ข่าวแรงงานก่อสร้าง

## ภูมิรัฐศาสตร์
- เศรษฐกิจโลกที่กระทบไทย
"""


def debug_secrets():
    print("=" * 50)
    print("DEBUG SECRETS")
    print("=" * 50)
    
    for name, val in [
        ("ANTHROPIC_API_KEY", ANTHROPIC_API_KEY),
        ("LINE_CHANNEL_ACCESS_TOKEN", LINE_TOKEN),
        ("LINE_USER_ID", LINE_USER_ID),
    ]:
        try:
            val.encode('ascii')
            ascii_ok = "OK"
        except UnicodeEncodeError as e:
            ascii_ok = f"FAIL at position {e.start}-{e.end}"
        
        print(f"{name}:")
        print(f"  Length: {len(val)}")
        print(f"  ASCII: {ascii_ok}")
        print(f"  First 10: [{val[:10]}]")
        print(f"  Last 10:  [{val[-10:]}]")
        
        # ดูแต่ละ byte ที่ไม่ใช่ ASCII
        bad_chars = [(i, ord(c)) for i, c in enumerate(val) if ord(c) > 127]
        if bad_chars:
            print(f"  Bad chars: {bad_chars[:10]}")
        print()
    print("=" * 50)


def fetch_news():
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=3000,
        tools=[{
            "type": "web_search_20250305",
            "name": "web_search",
            "max_uses": 5
        }],
        messages=[{"role": "user", "content": NEWS_PROMPT}]
    )
    text_parts = [b.text for b in response.content if b.type == "text"]
    return "\n".join(text_parts).strip()


def save_to_file(content):
    today = datetime.now().strftime("%Y-%m-%d")
    Path("news").mkdir(exist_ok=True)
    filepath = Path("news") / f"{today}.md"
    header = f"# News {today}\n\n"
    filepath.write_text(header + content, encoding="utf-8")
    return filepath, today


def send_line(content, today):
    repo_url = f"https://github.com/{GITHUB_REPO}/blob/main/news/{today}.md"
    body = content[:4200] + "\n...(cut)" if len(content) > 4200 else content
    
    message = (
        f"News {today}\n"
        f"---\n"
        f"{body}\n\n"
        f"Full: {repo_url}"
    )
    
    r = requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers={
            "Authorization": f"Bearer {LINE_TOKEN}",
            "Content-Type": "application/json"
        },
        json={
            "to": LINE_USER_ID,
            "messages": [{"type": "text", "text": message}]
        },
        timeout=30
    )
    r.raise_for_status()
    print(f"LINE sent: HTTP {r.status_code}")


if __name__ == "__main__":
    debug_secrets()
    
    print("Fetching news from Claude...")
    content = fetch_news()
    print(f"Got {len(content)} chars")
    
    print("Saving to file...")
    filepath, today = save_to_file(content)
    print(f"Saved: {filepath}")
    
    print("Sending LINE...")
    send_line(content, today)
    
    print("Done!")
