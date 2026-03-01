import os
import json
import feedparser
import requests
import google.generativeai as genai
import time

# 1. 환경 변수 체크
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')

# 2. 로그 및 DB 관리
DB_FILE = "news_db.json"

def save_log(msg):
    print(msg)
    try:
        data = load_db()
        if isinstance(data, list):
            # 로그용 딕셔너리가 없으면 생성
            data.append({"log_type": "system", "time": time.ctime(), "msg": msg})
        save_db(data)
    except:
        pass

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except:
                return []
    return []

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 3. Gemini 설정
try:
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
    else:
        save_log("❌ GEMINI_API_KEY is missing!")
except Exception as e:
    save_log(f"❌ Gemini Config Error: {e}")

def get_ai_insight(title, summary):
    prompt = f"게임 개발자 관점에서 한국어로 3줄 요약해줘.\n제목: {title}\n내용: {summary}"
    try:
        response = model.generate_content(prompt)
        return response.text if response else "Empty Response"
    except Exception as e:
        return f"🚨 [AI Error] {str(e)[:100]}"

def send_to_slack(text, link, source, title):
    if not SLACK_WEBHOOK_URL:
        save_log("❌ SLACK_WEBHOOK_URL is missing!")
        return
    
    payload = {
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*🛡️ [AI Game Sentinel] New from {source}*"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*제목: <{link}|{title}>*"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": text}}
        ]
    }
    res = requests.post(SLACK_WEBHOOK_URL, json=payload)
    if res.status_code != 200:
        save_log(f"❌ Slack Post Error: {res.status_code} - {res.text}")

def main():
    save_log("🚀 Crawler Started...")
    db = load_db()
    # 뉴스 데이터만 필터링 (로그 제외)
    processed_links = [item['link'] for item in db if 'link' in item]
    
    RSS_FEEDS = {
        "GeekNews": "https://news.hada.io/rss",
        "80Level": "https://80.lv/articles/rss/",
        "UnityBlog": "https://blog.unity.com/rss/topic/ai",
        "OpenAI": "https://openai.com/news/rss.xml"
    }

    for name, url in RSS_FEEDS.items():
        save_log(f"Checking {name}...")
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:1]: # 테스트용 각 1개
                if entry.link not in processed_links:
                    save_log(f"Found new in {name}: {entry.title}")
                    insight = get_ai_insight(entry.title, entry.get('summary', entry.title))
                    send_to_slack(insight, entry.link, name, entry.title)
                    db.append({"link": entry.link, "title": entry.title})
        except Exception as e:
            save_log(f"❌ RSS Error ({name}): {e}")
    
    save_db(db)
    save_log("✅ Crawler Finished.")

if __name__ == "__main__":
    main()
