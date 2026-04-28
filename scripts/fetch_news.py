import os
from datetime import datetime
from pathlib import Path
import anthropic
import requests

# ──────── CONFIG ────────
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
LINE_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
LINE_USER_ID = os.environ["LINE_USER_ID"]
GITHUB_REPO = os.environ.get("GITHUB_REPOSITORY", "")

NEWS_PROMPT = """สรุปข่าวสำคัญประจำวันของวันนี้ (ภาษาไทย) แบ่งเป็น 4 หมวด:

## 📈 ตลาดหุ้นไทย
- SET Index ปิดที่เท่าไหร่ +/- กี่จุด
- CRD.BK ราคาและความเคลื่อนไหว
- หุ้นกลุ่มก่อสร้างเด่นๆ

## 💰 ทอง + Bitcoin
- ราคาทองคำ (สมาคมค้าทอง)
- Bitcoin USD

## 🏗️ ข่าวก่อสร้างไทย
- โครงการรัฐ/เอกชนใหม่
- ราคาวัสดุก่อสร้าง (เหล็ก, ปูน)
- ข่าวแรงงานก่อสร้าง

## 🌏 ภูมิรัฐศาสตร์ที่กระทบไทย
- เศรษฐกิจโลก, การค้า, นโยบายที่กระทบไทย

ข้อกำหนด:
- bullet points สั้นๆ มีตัวเลขสำคัญ
- ไม่ต้องมีคำเกริ่นนำ
- ข้อมูลล่าสุด ณ วันนี้เท่านั้น
"""

# ──────── 1) เรียก Claude พร้อม web_search ────────
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

# ──────── 2) บันทึกเป็น markdown ────────
def save_to_file(content):
    today = datetime.now().strftime("%Y-%m-%d")
    Path("news").mkdir(exist_ok=True)
    filepath = Path("news") / f"{today}.md"
    header = f"# ข่าวประจำวันที่ {today}\n\n"
    filepath.write_text(header + content, encoding="utf-8")
    return filepath, today

# ──────── 3) ส่ง LINE Push Message ────────
def send_line(content, today):
    repo_url = f"https://github.com/{GITHUB_REPO}/blob/main/news/{today}.md"
    
    # LINE limit 5000 chars — เผื่อ header/footer
    body = content[:4200] + "\n...(ตัด)" if len(content) > 4200 else content
    
    message = (
        f"📰 ข่าวประจำวัน {today}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{body}\n\n"
        f"🔗 ดูเต็ม: {repo_url}"
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
    print(f"✅ LINE sent: HTTP {r.status_code}")

# ──────── MAIN ────────
if __name__ == "__main__":
    print("🔍 Fetching news from Claude...")
    content = fetch_news()
    print(f"   Got {len(content)} chars")
    
    print("💾 Saving to file...")
    filepath, today = save_to_file(content)
    print(f"   Saved: {filepath}")
    
    print("📲 Sending LINE...")
    send_line(content, today)
    
    print("🎉 Done!")
