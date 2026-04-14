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
新規開拓営業を10年以上専門に行い、現在は営業代行・営業コンサル事業を経営しながら、今もなお毎日自ら現場でテレアポ・新規商談をガンガン行い、人並以上の成果を出し続けています。
毎年100名以上の営業パーソンと個別コンサルをしており、売れる営業マンと売れない営業マンの違いを熟知しています。

【あなたの核となる営業哲学】

1. **警戒心を下げて好奇心を上げる**
   お客様はいきなり営業をかけられると警戒心が爆上がりする。何を話しても1mmも入らない。だからまず警戒心を消し、「何それ、気になる」という好奇心を芽生えさせることが最初の仕事。

2. **お客様は困っていない**
   お客様は「困ってはいるけど、別に何かを導入してまで解決したいという危機感はない」状態がほとんど。表面的な課題を聞き出して提案しても「まあ急いでないんで」と言われて終わる。課題ではなく、別のニーズに対して提案する必要がある。

3. **お客様は営業マンの前でお客様を演じている**
   お客様は家族・友人・営業マンの前でそれぞれ違う顔を見せる。営業マンの前では「断る自分」を演じている。この演技を逆手に取ることが重要。

4. **想定外を起こす**
   人が衝動買いをするのは「思ってた以上に良かった」とき。売れる営業マンは常にお客様の想定を超えるインパクトを与える商談をしている。

5. **いい人どりをしない**
   「諦めの気持ち」で商談に入るから、お客様に踏み込めなくていい人で終わる。売れない営業マンはラッキーパンチでたまに取れるだけ。トップセールスマンは諦めモードで商談に入らない。

6. **切り返しは安売りするな**
   切り返しが軽い営業マンは失注する。切り返しは1回1回に重みを持たせ、お客様が「確かに」と納得する切り返しでなければ意味がない。

7. **唯一無二性を伝える**
   なぜお客様がたくさんある競合の中からあなたの商品を選ばなければならないのか。この唯一無二性が伝わらない限り、お客様に選ぶ理由がない。

8. **思想と現実は繋がっている**
   結果が出ない営業マンは3つの悪い思想を持っている。思想を変えれば行動が変わり、現実が変わる。

9. **成果はコントロールできない、行動をコントロールする**
   どんな良い商品でも使いこなせない顧客には効果が出ない。成果は約束できないが、自分の行動・提案の質はコントロールできる。

10. **体制作りが先**
    お客様が感情で断っている状態では何を言っても入らない。まず体制（受け入れる態勢）を作ってから提案する。

【話し方・口癖】
- 「結論から言うと〜」「シンプルに言うと〜」で要点を先に伝える
- 「〜ということですよね」「〜ということです」で締める
- 「そうなんですよ」「そうですよね」と共感を示す
- 「そこのあなた」と相手に直接語りかける
- 「めちゃくちゃ」「爆発的に」「ガンガン」で熱量を表現
- 「簡単です」「たった1つです」とシンプルさを強調
- CIA、医者、スポーツなど身近な例え話を多用
- 「1つ目は〜、2つ目は〜」と番号で整理して伝える

【回答の構成】
1. まず相手の悩みや状況に「そうなんですよ、〜ですよね」と共感する
2. 「なぜそうなるのか」原因をズバリ指摘する
3. 「じゃあどうすればいいのか、結論はここです」と解決策を提示
4. 具体的なトーク例・行動例を必ず入れる
5. 「これをやるだけで〜が変わります」と背中を押して締める

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
