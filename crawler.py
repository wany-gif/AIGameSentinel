import os
import json
import feedparser
import requests
import google.generativeai as genai

# 1. 환경 변수 설정
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')

# Gemini AI 설정 - 더 강력한 최신 모델로 변경 시도
genai.configure(api_key=GEMINI_API_KEY)
# 최신 모델 이름 후보들: 'gemini-1.5-flash', 'gemini-1.5-flash-latest', 'gemini-1.5-pro'
MODEL_NAME = 'gemini-1.5-flash'
model = genai.GenerativeModel(MODEL_NAME)

DB_FILE = "news_db.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                return data if isinstance(data, list) else []
            except:
                return []
    return []

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_ai_insight(title, summary):
    # 만약 요약이 너무 짧으면 제목만 사용
    content = summary if len(summary) > 20 else title
    
    prompt = f"""
    당신은 시니어 게임 개발자이자 AI 뉴스 분석가입니다. 아래 뉴스를 한국어로 분석하세요.
    제목: {title}
    내용: {content}

    형식:
    1. 📝 핵심 요약 (한글 3줄)
    2. 💡 Game Dev Insight: (이 기술이 게임 개발에 미칠 영향 1문장)
    """
    try:
        if not GEMINI_API_KEY:
            return "❌ 에러: GEMINI_API_KEY가 설정되지 않았습니다."
            
        response = model.generate_content(prompt)
        # 응답이 비어있을 경우 체크
        if not response or not response.text:
            return "❌ 에러: Gemini가 빈 응답을 반환했습니다."
        return response.text
    except Exception as e:
        # 에러 원인을 최대한 상세하게 슬랙으로 보냄
        return f"🚨 [AI 분석 에러 발생]\n원인: {str(e)[:200]}"

def send_to_slack(text, link, source, title):
    payload = {
        "blocks": [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*🛡️ [AI Game Sentinel] ({source})*"}
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*제목: <{link}|{title}>*"}
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": text}
            },
            {"type": "divider"}
        ]
    }
    requests.post(SLACK_WEBHOOK_URL, json=payload)

def main():
    print(f"--- Crawler Start with {MODEL_NAME} ---")
    db = load_db()
    processed_links = [item['link'] for item in db]
    new_items = []

    for name, url in RSS_FEEDS.items():
        print(f"Checking {name}...")
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:2]:
                if entry.link not in processed_links:
                    print(f"Found new: {entry.title}")
                    insight = get_ai_insight(entry.title, entry.get('summary', entry.title))
                    send_to_slack(insight, entry.link, name, entry.title)
                    new_items.append({"link": entry.link})
        except Exception as e:
            print(f"Fetch Error in {name}: {e}")

    if new_items:
        save_db(db + new_items)
        print(f"Total {len(new_items)} items updated.")
    else:
        print("No new items.")

RSS_FEEDS = {
    "GeekNews": "https://news.hada.io/rss",
    "80Level": "https://80.lv/articles/rss/",
    "UnityBlog": "https://blog.unity.com/rss/topic/ai",
    "OpenAI": "https://openai.com/news/rss.xml"
}

if __name__ == "__main__":
    main()
