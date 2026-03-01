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

def get_ai_insight(title, summary):
    prompt = f"시니어 게임 개발자로서 다음 뉴스를 한국어로 3줄 요약하고, 인사이트를 1문장으로 적어줘.\n제목: {title}\n내용: {summary}"
    # 가장 호환성이 높은 모델 이름 리스트 순차 시도
    model_names = ['gemini-pro', 'models/gemini-1.5-flash', 'gemini-1.5-flash']
    
    last_error = "No model tried"
    for m_name in model_names:
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel(m_name)
            response = model.generate_content(prompt)
            if response and response.text:
                return response.text
        except Exception as e:
            last_error = str(e)
            continue # 다음 모델로 시도
            
    return f"🚨 [모든 모델 시도 실패] 마지막 에러: {last_error[:150]}"

def send_to_slack(text, link, source, title):
    if not SLACK_WEBHOOK_URL: return
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
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:1]:
                if entry.link not in processed_links:
                    insight = get_ai_insight(entry.title, entry.get('summary', entry.title))
                    send_to_slack(insight, entry.link, name, entry.title)
                    db.append({"link": entry.link, "title": entry.title})
        except:
            continue
    
    save_db(db)

if __name__ == "__main__":
    main()
