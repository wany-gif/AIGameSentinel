import os
import json
import feedparser
import requests
import google.generativeai as genai

# 1. 환경 변수 설정 (GitHub Secrets에서 가져옴)
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')

# Gemini AI 설정
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash-latest')

# 2. 뉴스 소스 (게임 개발자용 RSS)
RSS_FEEDS = {
    "GeekNews": "https://news.hada.io/rss",
    "80Level": "https://80.lv/articles/rss/",
    "UnityBlog": "https://blog.unity.com/rss/topic/ai",
    "OpenAI": "https://openai.com/news/rss.xml"
}

DB_FILE = "news_db.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                return data if isinstance(data, list) else []
            except (json.JSONDecodeError, ValueError):
                return []
    return []

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_ai_insight(title, summary):
    prompt = f"""
    너는 시니어 게임 개발자이자 AI 뉴스 큐레이터야. 아래 뉴스를 읽고 한국어로 분석해줘.
    영어 기사인 경우 반드시 한국어로 번역해서 요약해.

    뉴스 제목: {title}
    뉴스 내용: {summary}

    응답 형식 (반드시 다음 형식을 지켜):
    1. 📝 핵심 요약 (한글 3줄):
       - (첫 번째 줄)
       - (두 번째 줄)
       - (세 번째 줄)
    2. 💡 Game Dev Insight: (이 기술이 게임 개발, 그래픽, 최적화, NPC AI 등에 줄 구체적 영향 1문장)
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        error_msg = str(e)
        if "API_KEY_INVALID" in error_msg:
            return f"❌ AI 분석 실패: API 키가 올바르지 않습니다. (GitHub Secrets 확인 필요)"
        elif "quota" in error_msg.lower():
            return f"❌ AI 분석 실패: API 할당량 초과입니다. (잠시 후 다시 시도)"
        else:
            return f"❌ AI 분석 실패: {error_msg[:100]}..."

def send_to_slack(text, link, source, title):
    payload = {
        "blocks": [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*🛡️ [AI Game Sentinel] New Update from {source}*"}
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
    db = load_db()
    processed_links = [item['link'] for item in db]
    new_items = []

    for name, url in RSS_FEEDS.items():
        print(f"--- Checking {name} ({url}) ---")
        try:
            feed = feedparser.parse(url)
            # 수집된 기사가 없는 경우 출력
            if not feed.entries:
                print(f"⚠️ No entries found for {name}. Checking data structure...")
            
            for entry in feed.entries[:2]: # 각 사이트별 최신 2개씩 수집 (테스트용)
                if entry.link not in processed_links:
                    print(f"✅ New item found in {name}: {entry.title}")
                    insight = get_ai_insight(entry.title, entry.get('summary', entry.title))
                    send_to_slack(insight, entry.link, name, entry.title)
                    new_items.append({
                        "title": entry.title,
                        "link": entry.link,
                        "source": name,
                        "insight": insight
                    })
                else:
                    print(f"⏩ {entry.title} is already processed.")
        except Exception as e:
            print(f"❌ Error while fetching {name}: {e}")

    if new_items:
        save_db(db + new_items)
        print(f"🚀 {len(new_items)}건의 새로운 소식을 업데이트했습니다.")
    else:
        print("📭 새로운 소식이 없습니다.")

if __name__ == "__main__":
    main()
