"""
193本の動画字幕からヒョンさんのペルソナを徹底的に抽出・合成するスクリプト。
Step 1: バッチごとにClaudeで知識・口癖・哲学を抽出
Step 2: 全抽出結果を合成して詳細なペルソナドキュメントを生成
出力: data/persona.md
"""

import os
import json
import time
import anthropic
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

TRANSCRIPTS_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'transcripts.json')
INSIGHTS_CACHE_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'persona_insights_cache.json')
PERSONA_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'persona.md')

BATCH_SIZE = 10   # 1回のAPI呼び出しで処理する動画数
SLEEP_SEC = 25    # バッチ間のウェイト（レート制限対策）


def extract_batch_insights(client, videos, batch_num, total_batches):
    """1バッチ分の動画からヒョンさんの特徴を抽出する"""
    combined_text = ""
    for v in videos:
        combined_text += f"\n\n=== 動画ID: {v['video_id']} ===\n{v['text']}"

    print(f"  バッチ {batch_num}/{total_batches} を処理中（{len(videos)}本）...")

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": f"""以下はYouTubeチャンネル「Sales Labo」のヒョンさんの動画字幕テキストです。

この字幕から、ヒョンさんの営業哲学・特徴を以下の観点で抽出してください：

【抽出観点】
1. 繰り返し登場する営業哲学・考え方（タイトルと説明で）
2. 特徴的な口癖・フレーズ（実際の言葉をそのまま引用）
3. 使われている例え話・比喩・ストーリー（内容を具体的に）
4. お客様や営業マンに対する独自の見方・定義
5. 具体的な営業トーク例・スクリプト
6. よく批判する「ダメな営業マンの行動」

箇条書きで、なるべく実際の言葉を使って具体的に抽出してください。

--- 字幕テキスト ---
{combined_text}"""
        }]
    )
    return response.content[0].text


def synthesize_persona(client, all_insights_text):
    """全バッチの抽出結果を合成してペルソナドキュメントを生成する"""
    print("\nペルソナを合成中（Claude Sonnet）...")

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8000,
        messages=[{
            "role": "user",
            "content": f"""以下は「Sales Labo」チャンネルのヒョンさんの193本の動画すべてから抽出した営業哲学・口癖・特徴の生データです。

これらをもとに、AIがヒョンさんとして完全に振る舞えるよう、極めて詳細なペルソナドキュメントを作成してください。
AIシステムプロンプトとして使用するため、ヒョンさんの人格・哲学・話し方を再現するのに必要な情報をすべて網羅してください。

以下の構成で作成してください：

## プロフィール・経歴
（実績、現在の活動、専門性）

## 核となる営業哲学（重要度順）
各哲学について：
- タイトル（ヒョンさんが使う言葉で）
- 詳細な説明
- よく使う言い回し・フレーズ
- よく使う具体例・例え話

## 特徴的な口癖・フレーズ一覧
（動画から実際に抽出された言葉をそのまま、カテゴリ別に整理）
- 冒頭・導入のパターン
- 共感・同意の表現
- 強調するときの言い回し
- 締め・まとめのパターン

## よく使う例え話・ストーリー
（CIA、医者、スポーツ選手など、具体的な内容と文脈）

## シーン別アプローチと具体的トーク例
- テレアポ（アプローチ〜アポ獲得）
- 初回商談の進め方
- 提案・プレゼンのやり方
- クロージングの考え方と手法
- 断られたときの切り返し

## ダメな営業マンの典型パターン（批判・指摘のパターン）
（ヒョンさんがよく指摘する間違い・NG行動）

## 回答スタイル・話し方の構成
（どう始めて、どう展開して、どう締めるか。テンポ・エネルギー感も含めて）

---抽出データ---
{all_insights_text}"""
        }]
    )
    return response.content[0].text


def main():
    print("=== Sales Labo ペルソナ合成スクリプト ===\n")

    with open(TRANSCRIPTS_FILE, 'r', encoding='utf-8') as f:
        transcripts = json.load(f)
    print(f"{len(transcripts)}本の動画を読み込みました")

    client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

    # キャッシュ読み込み（中断再開用）
    insights_cache = {}
    if os.path.exists(INSIGHTS_CACHE_FILE):
        with open(INSIGHTS_CACHE_FILE, 'r', encoding='utf-8') as f:
            insights_cache = json.load(f)
        print(f"キャッシュ読み込み済み: {len(insights_cache)}バッチ完了")

    # バッチ処理
    batches = [transcripts[i:i+BATCH_SIZE] for i in range(0, len(transcripts), BATCH_SIZE)]
    total_batches = len(batches)
    print(f"\n{total_batches}バッチに分けて処理します（1バッチ={BATCH_SIZE}本）\n")

    print("=== Step 1: 各バッチから知識を抽出 ===")
    for i, batch in enumerate(batches):
        batch_key = str(i)
        if batch_key in insights_cache:
            print(f"  バッチ {i+1}/{total_batches}: スキップ（キャッシュ済み）")
            continue

        # レート制限・過負荷対策: リトライ付きで実行
        for attempt in range(5):
            try:
                insights = extract_batch_insights(client, batch, i+1, total_batches)
                break
            except (anthropic.RateLimitError, anthropic.APIStatusError) as e:
                wait = 60 * (attempt + 1)
                print(f"  エラー({type(e).__name__})のため {wait}秒待機...")
                time.sleep(wait)
        else:
            print(f"  バッチ {i+1} をスキップ（リトライ上限）")
            continue

        insights_cache[batch_key] = insights

        with open(INSIGHTS_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(insights_cache, f, ensure_ascii=False, indent=2)

        if i < total_batches - 1:
            print(f"  {SLEEP_SEC}秒待機中...")
            time.sleep(SLEEP_SEC)

    print(f"\n全{total_batches}バッチの抽出完了")

    # 全抽出結果を結合
    all_insights = "\n\n" + "="*50 + "\n\n".join(
        insights_cache[str(i)] for i in range(total_batches) if str(i) in insights_cache
    )

    # ペルソナ合成
    print("\n=== Step 2: ペルソナを合成 ===")
    persona_doc = synthesize_persona(client, all_insights)

    with open(PERSONA_FILE, 'w', encoding='utf-8') as f:
        f.write(persona_doc)

    print(f"\nペルソナドキュメントを保存しました: {PERSONA_FILE}")
    print(f"文字数: {len(persona_doc)}文字")
    print("\n完了！agent/agent.py が自動的にこのファイルを読み込みます。")


if __name__ == '__main__':
    main()
