import os
import chromadb
from sentence_transformers import SentenceTransformer
import anthropic
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

CHROMA_DIR = os.path.join(os.path.dirname(__file__), '..', 'chroma_db')
PERSONA_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'persona.md')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

_model = None
_collection = None
_client = None
_persona = None


def _load():
    global _model, _collection, _client, _persona
    if _model is None:
        _model = SentenceTransformer('intfloat/multilingual-e5-small')
    if _collection is None:
        db = chromadb.PersistentClient(path=CHROMA_DIR)
        _collection = db.get_collection('sales_labo')
    if _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    if _persona is None:
        if os.path.exists(PERSONA_FILE):
            with open(PERSONA_FILE, 'r', encoding='utf-8') as f:
                _persona = f.read()
        else:
            _persona = ""  # フォールバック: ペルソナファイルがない場合は空


def search_context(query, n_results=10):
    _load()
    embedding = _model.encode([query]).tolist()
    results = _collection.query(query_embeddings=embedding, n_results=n_results)
    docs = results['documents'][0]
    metas = results['metadatas'][0]
    return docs, metas


def _build_system_blocks(context, transcript=None):
    if _persona:
        persona_text = f"""あなたはYouTubeチャンネル「Sales Labo」の営業コンサルタント・ヒョンです。
以下のペルソナドキュメントに従って完全にヒョンとして振る舞ってください。

{_persona}
"""
    else:
        persona_text = """あなたはYouTubeチャンネル「Sales Labo」の営業コンサルタント・ヒョンです。
新規開拓営業を10年以上専門に行い、現在は営業代行・営業コンサル事業を経営しながら、今もなお毎日自ら現場でテレアポ・新規商談をガンガン行い、人並以上の成果を出し続けています。
毎年100名以上の営業パーソンと個別コンサルをしており、売れる営業マンと売れない営業マンの違いを熟知しています。

【核となる営業哲学】
1. 警戒心を下げて好奇心を上げる
2. お客様は困っていない（危機感がない状態）
3. お客様は営業マンの前でお客様を演じている
4. 想定外を起こす
5. いい人どりをしない
6. 切り返しは安売りするな
7. 唯一無二性を伝える
8. 成果はコントロールできない、行動をコントロールする
9. 体制作りが先

【話し方】
- 「結論から言うと〜」「シンプルに言うと〜」で要点を先に
- 「そうなんですよ」「そうですよね」と共感
- 「めちゃくちゃ」「ガンガン」で熱量を表現
- CIA、医者など例え話を多用
"""

    # ペルソナはキャッシュ対象（静的で大きいため）
    blocks = [
        {
            "type": "text",
            "text": persona_text,
            "cache_control": {"type": "ephemeral"}
        },
        {
            "type": "text",
            "text": f"【参考動画コンテンツ】\n以下は関連する実際の動画から取得したコンテンツです。回答の根拠・具体例として活用してください：\n{context}"
        }
    ]

    if transcript:
        blocks.append({
            "type": "text",
            "text": f"""【添付された商談文字起こし】
ユーザーが実際の商談・営業トークの文字起こしを添付しています。
フィードバックや質問があった場合、この文字起こしをもとに以下の観点で具体的なアドバイスをしてください：
- 良かった点（警戒心を下げる工夫、共感の取り方など）
- 改善できる点（課題の深掘り不足、切り返しの甘さなど）
- 具体的な改善トーク例
ヒョンとして、現場目線の実践的なフィードバックを行ってください。

--- 文字起こし開始 ---
{transcript}
--- 文字起こし終了 ---"""
        })

    return blocks


def ask(question, history=None, transcript=None):
    _load()
    docs, metas = search_context(question)
    context = '\n\n'.join([f"【参考】{d}" for d in docs])

    system_blocks = _build_system_blocks(context, transcript)

    messages = []
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": question})

    response = _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=system_blocks,
        messages=messages
    )
    return response.content[0].text


if __name__ == '__main__':
    print('Sales Labo AIエージェント（CLIモード）')
    print('終了するには Ctrl+C\n')
    history = []
    while True:
        try:
            q = input('あなた: ')
            if not q.strip():
                continue
            answer = ask(q, history)
            print(f'\nSales Labo: {answer}\n')
            history.append({"role": "user", "content": q})
            history.append({"role": "assistant", "content": answer})
        except KeyboardInterrupt:
            print('\n終了します')
            break
