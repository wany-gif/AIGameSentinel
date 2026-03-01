import os
import json
import feedparser
import requests
import google.generativeai as genai
import time

# 1. 환경 변수 체크
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')

# 2. DB 관리
DB_FILE = "news_db.json"

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

# 3. Gemini 설정 - 모델 이름 형식 수정 (models/ 추가)
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    # 여러 모델 후보를 시도해봅니다.
    model = genai.GenerativeModel('models/gemini-1.5-flash')

def get_ai_insight(title, summary):
    prompt = f"시니어 게임 개발자로서 다음 뉴스를 한국어로 3줄 요약하고, 인사이트를 1문장으로 적어줘.\n제목: {title}\n내용: {summary}"
    try:
        # 첫 번째 시도: gemini-1.5-flash
        response = model.generate_content(prompt)
        return response.text if response else "Empty Response"
    except Exception as e:
        # 실패 시 두 번째 시도: gemini-pro
        try:
            alt_model = genai.GenerativeModel('models/gemini-pro')
            response = alt_model.generate_content(prompt)
            return response.text if response else "Empty Response"
        except Exception as e2:
            return f"🚨 [AI Error] {str(e2)[:150]}"

def send_to_slack(text, link, source, title):
    payload = {
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*🛡️ [AI Game Sentinel] New from {source}*"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*제목: <{link}|{title}>*"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": text}}
        ]
    }
    requests.post(SLACK_WEBHOOK_URL, json=payload)

def main():
    db = load_db()
    processed_links = [item['link'] for item in db if 'link' in item]
    
    RSS_FEEDS = {
        "GeekNews": "https://news.hada.io/rss",
        "80Level": "https://80.lv/articles/rss/",
        "UnityBlog": "https://blog.unity.com/rss/topic/ai",
        "OpenAI": "https://openai.com/news/rss.xml"
    }

    for name, url in RSS_FEEDS.items():
        feed = feedparser.parse(url)
        for entry in feed.entries[:1]:
            if entry.link not in processed_links:
                insight = get_ai_insight(entry.title, entry.get('summary', entry.title))
                send_to_slack(insight, entry.link, name, entry.title)
                db.append({"link": entry.link, "title": entry.title})
    
    save_db(db)

if __name__ == "__main__":
    main()
