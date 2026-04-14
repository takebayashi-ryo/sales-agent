import os
import chromadb
from sentence_transformers import SentenceTransformer
import anthropic
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

CHROMA_DIR = os.path.join(os.path.dirname(__file__), '..', 'chroma_db')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

_model = None
_collection = None
_client = None

def _load():
    global _model, _collection, _client
    if _model is None:
        _model = SentenceTransformer('intfloat/multilingual-e5-small')
    if _collection is None:
        db = chromadb.PersistentClient(path=CHROMA_DIR)
        _collection = db.get_collection('sales_labo')
    if _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

def search_context(query, n_results=5):
    _load()
    embedding = _model.encode([query]).tolist()
    results = _collection.query(query_embeddings=embedding, n_results=n_results)
    docs = results['documents'][0]
    metas = results['metadatas'][0]
    return docs, metas

def ask(question, history=None):
    _load()
    docs, metas = search_context(question)
    context = '\n\n'.join([f"【参考】{d}" for d in docs])

    system_prompt = """あなたはYouTubeチャンネル「Sales Labo」の営業コンサルタント・ヒョンです。
約10年以上の新規開拓営業経験を持ち、現在は営業代行・営業コンサル事業を行いながら、今もなお現役で毎日新規商談を行っています。

【話し方・キャラクター】
- 最初に相手の悩みや状況に共感し、「そうなんですよ」「そうですよね」と受け止める
- 「結論から言うと〜」「シンプルに言うと〜」と要点を先に伝える
- 「〜ということですよね」「〜ということです」で締める
- 「そこのあなた」と視聴者に直接語りかける
- 「めちゃくちゃ」「爆発的に」「ガンガン」などの強い表現を使って熱量を伝える
- 「簡単です」「たった1つです」とシンプルさを強調する
- 具体的な例え話（医者、保険、CIA交渉術など）を使って分かりやすく説明する
- 1つ目、2つ目、ステップ1、ステップ2など番号で整理して伝える
- 相手が「なぜうまくいかないのか」の原因を明確に指摘してから解決策を伝える
- 難しい言葉は使わず、現場で今すぐ使えるトークや行動に落とし込む

【回答スタイル】
- まず相手の悩みに共感・問題の核心を指摘する
- 次に「じゃあどうすればいいのか」と解決策を提示する
- 最後に「これをやるだけで〜が変わります」と背中を押す
- 抽象論ではなく、具体的なトーク例や行動例を必ず入れる

参考にする動画の内容：
{context}
""".format(context=context)

    messages = []
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": question})

    response = _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=system_prompt,
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
