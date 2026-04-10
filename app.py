import streamlit as st
import sqlite3
import os
import json
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

# 初期化
init_db()

st.set_page_config(page_title="Sales Labo AI", page_icon="💼", layout="centered")
st.title("💼 Sales Labo AI コーチ")
st.caption("Sales Laboの動画をもとに、営業の悩みに答えます")

# サイドバー
with st.sidebar:
    st.header("顧客を選択")

    customers = get_customers()
    customer_names = [name for _, name in customers]
    customer_map = {name: cid for cid, name in customers}

    # 新規顧客追加
    new_name = st.text_input("新規顧客名を入力", placeholder="例: 山田商事")
    if st.button("追加") and new_name.strip():
        add_customer(new_name.strip())
        st.rerun()

    st.divider()

    # 顧客選択
    if customer_names:
        selected_name = st.radio("顧客一覧", customer_names)
        selected_id = customer_map[selected_name]

        if st.button("この顧客の履歴を削除", type="secondary"):
            delete_customer(selected_id)
            st.rerun()
    else:
        selected_name = None
        selected_id = None
        st.info("顧客を追加してください")

# メインエリア
if selected_id is None:
    st.info("サイドバーから顧客を選択または追加してください")
    st.stop()

st.subheader(f"{selected_name} との会話")

# セッション切り替え時に履歴を再読み込み
if st.session_state.get("current_customer_id") != selected_id:
    st.session_state.current_customer_id = selected_id
    st.session_state.messages = get_messages(selected_id)

# 会話表示
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 入力
if prompt := st.chat_input("営業の悩みを入力してください..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    save_message(selected_id, "user", prompt)
    with st.chat_message("user"):
        st.markdown(prompt)

    history = [m for m in st.session_state.messages[:-1]]
    with st.chat_message("assistant"):
        with st.spinner("考え中..."):
            answer = ask(prompt, history)
        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
    save_message(selected_id, "assistant", answer)
