import streamlit as st
import sqlite3
import os
import sys
import csv
import io
sys.path.insert(0, os.path.dirname(__file__))

from agent.agent import ask

DB_PATH = os.path.join(os.path.dirname(__file__), 'conversations.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS transcripts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER UNIQUE NOT NULL,
            filename TEXT,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    ''')
    conn.commit()
    conn.close()

def get_customers():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, name, created_at FROM customers ORDER BY created_at DESC')
    rows = c.fetchall()
    conn.close()
    return rows

def add_customer(name):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute('INSERT INTO customers (name) VALUES (?)', (name,))
        conn.commit()
        customer_id = c.lastrowid
    except sqlite3.IntegrityError:
        c.execute('SELECT id FROM customers WHERE name = ?', (name,))
        customer_id = c.fetchone()[0]
    conn.close()
    return customer_id

def get_messages(customer_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT role, content FROM messages WHERE customer_id = ? ORDER BY created_at', (customer_id,))
    rows = c.fetchall()
    conn.close()
    return [{"role": r, "content": content} for r, content in rows]

def save_message(customer_id, role, content):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO messages (customer_id, role, content) VALUES (?, ?, ?)', (customer_id, role, content))
    conn.commit()
    conn.close()

def delete_customer(customer_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM messages WHERE customer_id = ?', (customer_id,))
    c.execute('DELETE FROM transcripts WHERE customer_id = ?', (customer_id,))
    c.execute('DELETE FROM customers WHERE id = ?', (customer_id,))
    conn.commit()
    conn.close()

def save_transcript(customer_id, filename, content):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO transcripts (customer_id, filename, content)
        VALUES (?, ?, ?)
        ON CONFLICT(customer_id) DO UPDATE SET filename=excluded.filename, content=excluded.content, created_at=CURRENT_TIMESTAMP
    ''', (customer_id, filename, content))
    conn.commit()
    conn.close()

def get_transcript(customer_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT filename, content FROM transcripts WHERE customer_id = ?', (customer_id,))
    row = c.fetchone()
    conn.close()
    return row  # (filename, content) or None

def delete_transcript(customer_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM transcripts WHERE customer_id = ?', (customer_id,))
    conn.commit()
    conn.close()

def extract_text_from_file(uploaded_file):
    """ファイル種別に応じてテキストを抽出する"""
    name = uploaded_file.name.lower()
    content_bytes = uploaded_file.read()

    if name.endswith(".pdf"):
        import pdfplumber
        with pdfplumber.open(io.BytesIO(content_bytes)) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)

    elif name.endswith(".docx"):
        from docx import Document
        doc = Document(io.BytesIO(content_bytes))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

    elif name.endswith(".csv"):
        try:
            text = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = content_bytes.decode("shift_jis", errors="replace")
        reader = csv.reader(io.StringIO(text))
        return "\n".join(",".join(row) for row in reader)

    else:  # .txt / .md
        try:
            return content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return content_bytes.decode("shift_jis", errors="replace")

init_db()

st.set_page_config(page_title="Sales Labo AI", page_icon="S", layout="centered")

# スワイプでサイドバーを開く（スマホ対応）
st.markdown("""
<script>
(function() {
    let startX = 0;
    let startY = 0;
    document.addEventListener('touchstart', function(e) {
        startX = e.touches[0].clientX;
        startY = e.touches[0].clientY;
    }, { passive: true });
    document.addEventListener('touchend', function(e) {
        const dx = e.changedTouches[0].clientX - startX;
        const dy = e.changedTouches[0].clientY - startY;
        if (startX < 30 && dx > 70 && Math.abs(dy) < 100) {
            const btn = document.querySelector('[data-testid="stSidebarCollapsedControl"] button');
            if (btn) btn.click();
        }
    }, { passive: true });
})();
</script>
""", unsafe_allow_html=True)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .app-header {
        padding: 2.5rem 0 1.5rem 0;
        border-bottom: 1px solid rgba(255,255,255,0.08);
        margin-bottom: 2rem;
    }
    .app-title {
        font-size: 1.75rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        color: #ffffff;
        margin: 0;
    }
    .app-subtitle {
        font-size: 0.875rem;
        color: rgba(255,255,255,0.4);
        margin-top: 0.35rem;
        font-weight: 400;
    }

    .section-label {
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: rgba(255,255,255,0.3);
        margin: 1.2rem 0 0.6rem 0;
    }

    /* 新規トークボタン */
    .new-chat-btn {
        display: flex;
        align-items: center;
        gap: 8px;
        width: 100%;
        padding: 0.55rem 0.9rem;
        background: rgba(255,255,255,0.06);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 8px;
        color: rgba(255,255,255,0.85);
        font-size: 0.875rem;
        font-weight: 500;
        cursor: pointer;
        transition: background 0.15s;
        font-family: 'Inter', sans-serif;
        text-align: left;
    }
    .new-chat-btn:hover {
        background: rgba(255,255,255,0.1);
    }

    /* 会話リストアイテム */
    .chat-item {
        display: flex;
        align-items: center;
        justify-content: space-between;
        width: 100%;
        padding: 0.5rem 0.75rem;
        border-radius: 7px;
        cursor: pointer;
        transition: background 0.12s;
        margin-bottom: 2px;
    }
    .chat-item:hover {
        background: rgba(255,255,255,0.06);
    }
    .chat-item.active {
        background: rgba(255,255,255,0.1);
    }
    .chat-item-name {
        font-size: 0.875rem;
        color: rgba(255,255,255,0.8);
        font-weight: 400;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 150px;
    }
    .chat-item.active .chat-item-name {
        color: #ffffff;
        font-weight: 500;
    }

    /* 顧客ヘッダー */
    .customer-heading {
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: rgba(255,255,255,0.3);
        margin-bottom: 1.5rem;
    }

    .empty-state {
        text-align: center;
        padding: 5rem 2rem;
        color: rgba(255,255,255,0.25);
        font-size: 0.9rem;
        line-height: 1.8;
    }

    [data-testid="stSidebar"] {
        border-right: 1px solid rgba(255,255,255,0.06);
    }

    [data-testid="stChatInput"] textarea {
        font-family: 'Inter', sans-serif;
        font-size: 0.9rem;
    }

    [data-testid="stSidebar"] .stButton button {
        font-size: 0.8rem;
        font-weight: 500;
        border-radius: 8px;
    }

    hr {
        border-color: rgba(255,255,255,0.07) !important;
        margin: 0.75rem 0 !important;
    }

    /* 新規トーク入力欄 */
    .new-chat-input {
        margin-top: 0.5rem;
    }

    /* コピーボタン */
    .copy-btn {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        margin-top: 6px;
        padding: 4px 10px;
        background: rgba(255,255,255,0.06);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 6px;
        color: rgba(255,255,255,0.45);
        font-size: 0.75rem;
        font-family: 'Inter', sans-serif;
        cursor: pointer;
        transition: all 0.15s;
    }
    .copy-btn:hover {
        background: rgba(255,255,255,0.1);
        color: rgba(255,255,255,0.75);
    }
    .copy-btn.copied {
        color: #4ade80;
        border-color: rgba(74,222,128,0.3);
    }
</style>
""", unsafe_allow_html=True)

# セッション初期化
if "selected_customer_id" not in st.session_state:
    st.session_state.selected_customer_id = None
if "show_new_chat_input" not in st.session_state:
    st.session_state.show_new_chat_input = False
if "transcript_content" not in st.session_state:
    st.session_state.transcript_content = None
if "transcript_filename" not in st.session_state:
    st.session_state.transcript_filename = None

# サイドバー
with st.sidebar:
    st.markdown('<div style="font-size:1rem;font-weight:700;color:rgba(255,255,255,0.9);padding:0.5rem 0 1.5rem 0;">Sales Labo AI</div>', unsafe_allow_html=True)

    # 新規トークボタン
    if st.button("＋  新規トーク", use_container_width=True):
        st.session_state.show_new_chat_input = not st.session_state.show_new_chat_input

    # 新規トーク入力欄
    if st.session_state.show_new_chat_input:
        new_name = st.text_input("", placeholder="タイトルを入力...", label_visibility="collapsed", key="new_name_input")
        if new_name.strip() and st.button("作成", use_container_width=True):
            cid = add_customer(new_name.strip())
            st.session_state.selected_customer_id = cid
            st.session_state.show_new_chat_input = False
            st.rerun()

    # 会話リスト
    customers = get_customers()
    if customers:
        st.markdown('<div class="section-label">会話履歴</div>', unsafe_allow_html=True)
        for cid, name, created_at in customers:
            is_active = st.session_state.selected_customer_id == cid
            active_class = "active" if is_active else ""
            col1, col2 = st.columns([5, 1])
            with col1:
                if st.button(name, key=f"customer_{cid}", use_container_width=True):
                    st.session_state.selected_customer_id = cid
                    st.rerun()
            with col2:
                if st.button("×", key=f"delete_{cid}"):
                    delete_customer(cid)
                    if st.session_state.selected_customer_id == cid:
                        st.session_state.selected_customer_id = None
                    st.rerun()

# メインエリア
st.markdown("""
<div class="app-header">
    <div class="app-title">Sales Labo AI</div>
    <div class="app-subtitle">193本の動画をもとに、営業の悩みに答えます</div>
</div>
""", unsafe_allow_html=True)

selected_id = st.session_state.selected_customer_id

if selected_id is None:
    st.markdown("""
    <div class="empty-state">
        サイドバーの「＋ 新規トーク」から<br>タイトルをつけて会話を始めてください
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# 顧客名取得
customers = get_customers()
customer_map = {cid: name for cid, name, _ in customers}
selected_name = customer_map.get(selected_id, "")

st.markdown(f'<div class="customer-heading" style="font-size:1rem;font-weight:600;color:rgba(255,255,255,0.75);letter-spacing:0;text-transform:none;">{selected_name}</div>', unsafe_allow_html=True)

if st.session_state.get("current_customer_id") != selected_id:
    st.session_state.current_customer_id = selected_id
    st.session_state.messages = get_messages(selected_id)
    transcript_row = get_transcript(selected_id)
    if transcript_row:
        st.session_state.transcript_filename = transcript_row[0]
        st.session_state.transcript_content = transcript_row[1]
    else:
        st.session_state.transcript_filename = None
        st.session_state.transcript_content = None

# 添付中の文字起こしバッジ表示
if st.session_state.transcript_content:
    col1, col2 = st.columns([8, 1])
    with col1:
        st.markdown(f'<div style="font-size:0.8rem;color:rgba(255,255,255,0.5);padding:0.3rem 0;">📎 <span style="color:rgba(255,255,255,0.75);">{st.session_state.transcript_filename}</span> を添付中</div>', unsafe_allow_html=True)
    with col2:
        if st.button("×", key="remove_transcript", help="添付を解除"):
            delete_transcript(selected_id)
            st.session_state.transcript_content = None
            st.session_state.transcript_filename = None
            st.rerun()

def render_assistant_message(content, msg_id):
    import json
    json_content = json.dumps(content)  # 特殊文字を安全にエンコード
    st.markdown(content)
    st.markdown(f"""
<button class="copy-btn" id="copy-btn-{msg_id}"
    onclick="(function(){{
        var text = {json_content};
        navigator.clipboard.writeText(text).then(function(){{
            var btn = document.getElementById('copy-btn-{msg_id}');
            btn.innerText = 'コピーしました';
            btn.classList.add('copied');
            setTimeout(function(){{ btn.innerText = 'コピー'; btn.classList.remove('copied'); }}, 2000);
        }});
    }})()">コピー</button>
""", unsafe_allow_html=True)

# 既存メッセージを描画（forループのみで行い、インライン描画はしない）
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            render_assistant_message(msg["content"], f"hist-{i}")
        else:
            st.markdown(msg["content"])

# 返答待ち中ならスピナーを表示してAIを呼び出す
if st.session_state.get("_pending_prompt"):
    with st.chat_message("assistant"):
        with st.spinner(""):
            try:
                history = [m for m in st.session_state.messages]
                answer = ask(
                    st.session_state._pending_prompt,
                    history,
                    transcript=st.session_state.transcript_content
                )
            except Exception as e:
                answer = f"エラーが発生しました: {type(e).__name__}: {e}"
        render_assistant_message(answer, f"new-{len(st.session_state.messages)}")
    st.session_state.messages.append({"role": "assistant", "content": answer})
    save_message(selected_id, "assistant", answer)
    del st.session_state["_pending_prompt"]
    st.rerun()

# 全てコピーボタン（アシスタントの返答が1件以上あるとき表示）
assistant_messages = [m for m in st.session_state.messages if m["role"] == "assistant"]
if assistant_messages and not st.session_state.get("_pending_prompt"):
    import json
    all_text = "\n\n---\n\n".join(m["content"] for m in assistant_messages)
    json_all = json.dumps(all_text)
    st.markdown(f"""
<button class="copy-btn" id="copy-all-btn" style="margin: 0.5rem 0 1rem 0; font-size:0.8rem;"
    onclick="(function(){{
        var text = {json_all};
        navigator.clipboard.writeText(text).then(function(){{
            var btn = document.getElementById('copy-all-btn');
            btn.innerText = '全てコピーしました';
            btn.classList.add('copied');
            setTimeout(function(){{ btn.innerText = '全ての返答をコピー'; btn.classList.remove('copied'); }}, 2000);
        }});
    }})()">全ての返答をコピー</button>
""", unsafe_allow_html=True)

# チャット入力
msg = st.chat_input("営業の悩みを入力してください", accept_file=True, file_type=["txt", "md", "pdf", "docx", "csv"])
if msg:
    prompt = msg.text if msg.text else ""

    # ファイルが添付されていたら文字起こしとして保存
    if msg.files:
        uploaded_file = msg.files[0]
        try:
            transcript_text = extract_text_from_file(uploaded_file)
        except Exception as e:
            transcript_text = ""
            st.error(f"ファイルの読み込みに失敗しました: {e}")
        save_transcript(selected_id, uploaded_file.name, transcript_text)
        st.session_state.transcript_filename = uploaded_file.name
        st.session_state.transcript_content = transcript_text
        if not prompt:
            prompt = f"「{uploaded_file.name}」を添付しました。この商談のフィードバックをお願いします。"

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        save_message(selected_id, "user", prompt)
        st.session_state["_pending_prompt"] = prompt
    st.rerun()
