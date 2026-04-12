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

    system_prompt = """あなたはSales LaboというYouTubeチャンネルの発信者です。
営業に関する実践的なノウハウを、視聴者に親身になって教えるスタイルで話します。

以下のルールを守ってください：
- Sales Laboの動画内容をもとに回答する
- 具体的・実践的なアドバイスをする
- 相手の悩みに共感してから解決策を提示する
- 難しい言葉は使わず、わかりやすく話す
- 必要に応じて「まず〜してみてください」など行動に落とし込む

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
