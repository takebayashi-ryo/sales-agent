import streamlit as st
import sqlite3
import os
import sys
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
    c.execute('DELETE FROM customers WHERE id = ?', (customer_id,))
    conn.commit()
    conn.close()

init_db()

st.set_page_config(page_title="Sales Labo AI", page_icon="S", layout="centered")

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
</style>
""", unsafe_allow_html=True)

# セッション初期化
if "selected_customer_id" not in st.session_state:
    st.session_state.selected_customer_id = None
if "show_new_chat_input" not in st.session_state:
    st.session_state.show_new_chat_input = False

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

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("営業の悩みを入力してください"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    save_message(selected_id, "user", prompt)
    with st.chat_message("user"):
        st.markdown(prompt)

    history = [m for m in st.session_state.messages[:-1]]
    with st.chat_message("assistant"):
        with st.spinner(""):
            answer = ask(prompt, history)
        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
    save_message(selected_id, "assistant", answer)
