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
    c.execute('SELECT id, name FROM customers ORDER BY created_at DESC')
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

    /* ヘッダー */
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
        color: rgba(255,255,255,0.45);
        margin-top: 0.35rem;
        font-weight: 400;
    }

    /* 顧客名見出し */
    .customer-header {
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: rgba(255,255,255,0.35);
        margin-bottom: 1.25rem;
    }

    /* 空状態 */
    .empty-state {
        text-align: center;
        padding: 4rem 2rem;
        color: rgba(255,255,255,0.3);
        font-size: 0.9rem;
        line-height: 1.7;
    }

    /* サイドバー調整 */
    [data-testid="stSidebar"] {
        border-right: 1px solid rgba(255,255,255,0.06);
    }
    [data-testid="stSidebar"] .block-container {
        padding-top: 2rem;
    }

    /* ラジオボタンを顧客リストらしく */
    [data-testid="stSidebar"] [data-testid="stRadio"] label {
        font-size: 0.9rem;
        font-weight: 400;
        padding: 0.3rem 0;
    }

    /* チャット入力 */
    [data-testid="stChatInput"] textarea {
        font-family: 'Inter', sans-serif;
        font-size: 0.9rem;
    }

    /* ボタン */
    [data-testid="stSidebar"] .stButton button {
        font-size: 0.8rem;
        font-weight: 500;
        border-radius: 8px;
    }

    /* divider */
    hr {
        border-color: rgba(255,255,255,0.07) !important;
    }

    /* メッセージ */
    [data-testid="stChatMessage"] {
        border-radius: 12px;
    }
</style>
""", unsafe_allow_html=True)

# ヘッダー
st.markdown("""
<div class="app-header">
    <div class="app-title">Sales Labo AI</div>
    <div class="app-subtitle">193本の動画をもとに、営業の悩みに答えます</div>
</div>
""", unsafe_allow_html=True)

# サイドバー
with st.sidebar:
    st.markdown('<div class="customer-header">Clients</div>', unsafe_allow_html=True)

    customers = get_customers()
    customer_names = [name for _, name in customers]
    customer_map = {name: cid for cid, name in customers}

    new_name = st.text_input("", placeholder="顧客名を入力して追加", label_visibility="collapsed")
    if st.button("+ 追加", use_container_width=True) and new_name.strip():
        add_customer(new_name.strip())
        st.rerun()

    if customer_names:
        st.divider()
        selected_name = st.radio("", customer_names, label_visibility="collapsed")
        selected_id = customer_map[selected_name]

        st.divider()
        if st.button("履歴を削除", use_container_width=True, type="secondary"):
            delete_customer(selected_id)
            st.rerun()
    else:
        selected_name = None
        selected_id = None

# メインエリア
if selected_id is None:
    st.markdown("""
    <div class="empty-state">
        サイドバーから顧客を追加して<br>会話を始めてください
    </div>
    """, unsafe_allow_html=True)
    st.stop()

st.markdown(f'<div class="customer-header">{selected_name}</div>', unsafe_allow_html=True)

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
