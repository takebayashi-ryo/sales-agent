import streamlit as st
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from agent.agent import ask

st.set_page_config(page_title="Sales Labo AI", page_icon="💼", layout="centered")
st.title("💼 Sales Labo AI コーチ")
st.caption("Sales Laboの動画をもとに、営業の悩みに答えます")

if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.history = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("営業の悩みを入力してください..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("考え中..."):
            answer = ask(prompt, st.session_state.history)
        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.session_state.history.append({"role": "user", "content": prompt})
    st.session_state.history.append({"role": "assistant", "content": answer})
