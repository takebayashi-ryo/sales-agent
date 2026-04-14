import os
import re
import json
import chromadb
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

TRANSCRIPTS_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'transcripts.json')
CHROMA_DIR = os.path.join(os.path.dirname(__file__), '..', 'chroma_db')
CHUNK_SIZE = 600   # 文字数
OVERLAP = 120      # オーバーラップ文字数

def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=OVERLAP):
    """文境界を考慮しオーバーラップありでテキストをチャンク分割する"""
    sentences = re.split(r'(?<=[。！？\n])', text)
    sentences = [s for s in sentences if s.strip()]

    chunks = []
    current = ""
    for sentence in sentences:
        if len(current) + len(sentence) <= chunk_size:
            current += sentence
        else:
            if current.strip():
                chunks.append(current.strip())
            # オーバーラップ: 前のチャンクの末尾を引き継ぐ
            overlap_text = current[-overlap:] if len(current) > overlap else current
            current = overlap_text + sentence

    if current.strip():
        chunks.append(current.strip())

    return chunks

def main():
    print('字幕データを読み込み中...')
    with open(TRANSCRIPTS_FILE, 'r', encoding='utf-8') as f:
        transcripts = json.load(f)

    print(f'モデルを読み込み中...')
    model = SentenceTransformer('intfloat/multilingual-e5-small')

    client = chromadb.PersistentClient(path=CHROMA_DIR)
    try:
        client.delete_collection('sales_labo')
    except Exception:
        pass
    collection = client.create_collection('sales_labo')

    all_chunks = []
    all_ids = []
    all_metadatas = []

    for video in transcripts:
        chunks = chunk_text(video['text'])
        for j, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            all_ids.append(f"{video['video_id']}_{j}")
            all_metadatas.append({'video_id': video['video_id'], 'url': video['url']})

    print(f'合計 {len(all_chunks)} チャンクをベクトル化中（旧: 2226 → 改善後）...')

    batch_size = 100
    for i in range(0, len(all_chunks), batch_size):
        batch_chunks = all_chunks[i:i+batch_size]
        batch_ids = all_ids[i:i+batch_size]
        batch_metas = all_metadatas[i:i+batch_size]

        embeddings = model.encode(batch_chunks, show_progress_bar=False).tolist()
        collection.add(documents=batch_chunks, embeddings=embeddings, ids=batch_ids, metadatas=batch_metas)
        print(f'  {min(i+batch_size, len(all_chunks))}/{len(all_chunks)} 完了')

    print(f'\nインデックス構築完了！→ {CHROMA_DIR}')
    print(f'チャンク数: {len(all_chunks)}（オーバーラップ{OVERLAP}文字付き、文境界分割）')

if __name__ == '__main__':
    main()
