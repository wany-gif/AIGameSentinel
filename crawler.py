import os
import json
import feedparser
import requests
import google.generativeai as genai
import time

# 1. 환경 변수 설정 (GitHub Secrets에서 가져옴)
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
# 두 채널의 웹훅 주소 (없으면 gamedev로 대체)
WEBHOOK_GAMEDEV = os.environ.get('SLACK_WEBHOOK_URL')
WEBHOOK_GENERAL = os.environ.get('SLACK_WEBHOOK_URL_GENERAL')

# 2. 뉴스 소스 정의 및 카테고리 분류
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

def get_ai_insight(title, summary):
    prompt = f"시니어 게임 개발자로서 다음 뉴스를 한국어로 3줄 요약하고, 인사이트를 1문장으로 적어줘.\n제목: {title}\n내용: {summary}"
    # 호환성 높은 모델 리스트 순차 시도
    model_names = ['gemini-pro', 'models/gemini-1.5-flash', 'gemini-1.5-flash']
    
    last_error = ""
    for m_name in model_names:
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel(m_name)
            response = model.generate_content(prompt)
            if response and response.text: return response.text
        except Exception as e:
            last_error = str(e)
            continue
    return f"🚨 [AI 분석 실패] {last_error[:100]}"

def send_to_slack(text, link, source, title, category):
    # 카테고리에 따라 웹훅 선택
    webhook_url = WEBHOOK_GAMEDEV if category == "gamedev" else (WEBHOOK_GENERAL or WEBHOOK_GAMEDEV)
    
    payload = {
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*🛡️ [AI Game Sentinel] ({source})*"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*제목: <{link}|{title}>*"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": text}},
            {"type": "divider"}
        ]
    }
    requests.post(webhook_url, json=payload)

def main():
    db = load_db()
    processed_links = [item['link'] for item in db if 'link' in item]
    new_items = []

    for category, feeds in RSS_FEEDS.items():
        for name, url in feeds.items():
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:1]: # 각 소스별 최신 1개씩 수집
                    if entry.link not in processed_links:
                        insight = get_ai_insight(entry.title, entry.get('summary', entry.title))
                        send_to_slack(insight, entry.link, name, entry.title, category)
                        new_items.append({"link": entry.link, "title": entry.title})
                        time.sleep(1) # API 할당량 보호
            except: continue
    
    if new_items:
        save_db(db + new_items)

if __name__ == "__main__":
    main()
