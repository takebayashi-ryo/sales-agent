import os
import json
import time
import random
from googleapiclient.discovery import build
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
CHANNEL_ID = os.getenv('CHANNEL_ID')
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'transcripts.json')
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'

def get_all_video_ids(youtube, channel_id):
    video_ids = []
    next_page_token = None
    while True:
        res = youtube.search().list(
            channelId=channel_id,
            part='id',
            type='video',
            maxResults=50,
            pageToken=next_page_token
        ).execute()
        for item in res.get('items', []):
            video_ids.append(item['id']['videoId'])
        next_page_token = res.get('nextPageToken')
        if not next_page_token:
            break
    return video_ids

def extract_transcript_from_response(data):
    try:
        panel = data['actions'][0]['updateEngagementPanelAction']['content']['transcriptRenderer']['content']['transcriptSearchPanelRenderer']
        segments = panel['body']['transcriptSegmentListRenderer']['initialSegments']
        texts = []
        for seg in segments:
            runs = seg['transcriptSegmentRenderer']['snippet']['runs']
            for run in runs:
                t = run['text'].strip()
                if t:
                    texts.append(t)
        return ' '.join(texts)
    except (KeyError, IndexError):
        return None

def get_transcript_playwright(page, video_id):
    url = f'https://www.youtube.com/watch?v={video_id}'
    try:
        page.goto(url, wait_until='domcontentloaded', timeout=30000)
        time.sleep(random.uniform(3, 5))

        expand = page.locator('#expand')
        if expand.count() == 0:
            return None
        expand.first.click()
        time.sleep(random.uniform(1, 2))

        btn = page.get_by_role('button', name='文字起こしを表示')
        if btn.count() == 0:
            return None

        with page.expect_response(lambda r: 'get_transcript' in r.url, timeout=15000) as resp_info:
            btn.first.click()

        resp = resp_info.value
        if resp.status != 200:
            return None

        data = resp.json()
        return extract_transcript_from_response(data)

    except Exception as e:
        print(f'  → エラー: {type(e).__name__}')
        return None

def main():
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

    print('動画IDを取得中...')
    video_ids = get_all_video_ids(youtube, CHANNEL_ID)
    print(f'{len(video_ids)}本の動画を発見')

    results = []
    done_ids = set()
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            results = json.load(f)
        done_ids = {r['video_id'] for r in results}
        print(f'既存の進捗: {len(done_ids)}本完了済み')

    total = len(video_ids)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = browser.new_context(locale='ja-JP', user_agent=UA)
        context.add_init_script('Object.defineProperty(navigator, "webdriver", {get: () => undefined})')
        page = context.new_page()

        # YouTubeトップを先に開いてセッション確立
        page.goto('https://www.youtube.com', wait_until='domcontentloaded', timeout=30000)
        time.sleep(3)

        for i, video_id in enumerate(video_ids):
            if video_id in done_ids:
                print(f'[{i+1}/{total}] スキップ（取得済み）: {video_id}')
                continue

            print(f'[{i+1}/{total}] 字幕取得中: {video_id}')
            text = get_transcript_playwright(page, video_id)

            if text:
                results.append({
                    'video_id': video_id,
                    'url': f'https://www.youtube.com/watch?v={video_id}',
                    'text': text
                })
                with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                print(f'  → 成功 ({len(text)}文字)')
            else:
                print(f'  → 字幕なし、スキップ')

            time.sleep(random.uniform(3, 6))

        browser.close()

    print(f'\n完了！{len(results)}本の字幕を保存しました → {OUTPUT_FILE}')

if __name__ == '__main__':
    main()
