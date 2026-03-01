import os
import json
import feedparser
import requests
import google.generativeai as genai
import time
import re

# 1. 환경 변수 설정
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
WEBHOOK_GAMEDEV = os.environ.get('SLACK_WEBHOOK_URL')
WEBHOOK_GENERAL = os.environ.get('SLACK_WEBHOOK_URL_GENERAL')

# 2. HTML 태그 및 특수문자 제거 함수
def clean_html(text):
    if not text: return ""
    clean = re.compile('<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});')
    return re.sub(clean, '', text).strip()

# 3. DB 관리
DB_FILE = "news_db.json"
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            try: return json.load(f)
            except: return []
    return []

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 4. Gemini 호출 (가장 안정적인 모델명 사용)
def get_ai_insight(title, summary):
    clean_title = clean_html(title)
    clean_summary = clean_html(summary)
    
    prompt = f"시니어 게임 개발자로서 다음 뉴스를 한국어로 3줄 요약하고 인사이트를 1문장으로 적어줘.\n제목: {clean_title}\n내용: {clean_summary}"
    
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        # 최신 SDK에서는 'gemini-1.5-flash'를 바로 사용합니다.
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        if response and response.text:
            return response.text
    except Exception as e:
        # 실패 시 1.0 Pro 모델로 시도
        try:
            model_alt = genai.GenerativeModel('gemini-pro')
            response = model_alt.generate_content(prompt)
            return response.text
        except:
            return f"🚨 [분석 실패] {str(e)[:100]}"
    return "🚨 [분석 실패] 응답 없음"

def send_to_slack(text, link, source, title, category):
    webhook_url = WEBHOOK_GAMEDEV if category == "gamedev" else (WEBHOOK_GENERAL or WEBHOOK_GAMEDEV)
    clean_title = clean_html(title)
    
    payload = {
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*🛡️ [{source}] 뉴 업데이트*"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*제목: <{link}|{clean_title}>*"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": text}},
            {"type": "divider"}
        ]
    }
    requests.post(webhook_url, json=payload)

def main():
    db = load_db()
    processed_links = [item['link'] for item in db if 'link' in item]
    
    RSS_FEEDS = {
        "gamedev": {
            "UnrealEngine": "https://www.unrealengine.com/en-US/rss",
            "UnityBlog": "https://blog.unity.com/rss/topic/ai",
            "80Level": "https://80.lv/articles/rss/",
            "GameDeveloper": "https://www.gamedeveloper.com/rss.xml"
        },
        "general": {
            "OpenAI": "https://openai.com/news/rss.xml",
            "DeepMind": "https://deepmind.google/blog/rss.xml",
            "MicrosoftAI": "https://blogs.microsoft.com/ai/feed/",
            "GeekNews": "https://news.hada.io/rss"
        }
    }

    new_items = []
    for category, feeds in RSS_FEEDS.items():
        for name, url in feeds.items():
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:1]:
                    if entry.link not in processed_links:
                        insight = get_ai_insight(entry.title, entry.get('summary', entry.title))
                        send_to_slack(insight, entry.link, name, entry.title, category)
                        new_items.append({"link": entry.link, "title": entry.title})
                        time.sleep(2)
            except: continue
    
    if new_items:
        save_db(db + new_items)

if __name__ == "__main__":
    main()
