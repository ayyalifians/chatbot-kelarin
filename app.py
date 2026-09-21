import os
import json

import streamlit as st
from dotenv import load_dotenv

st.set_page_config(page_title="Kelarin", page_icon="📝")

load_dotenv()
if not os.getenv("GROQ_API_KEY"):
    st.error("GROQ_API_KEY belum diatur. Isi di file .env, lalu jalankan ulang aplikasinya.")
    st.stop()

from groq import (
    APIConnectionError,
    RateLimitError,
    AuthenticationError,
    APIStatusError,
)

import cli  # memakai ulang client, fungsi history, dan fungsi to-do dari versi console
from prompts import APP_NAME, SLOGAN

st.title(f"📝 {APP_NAME}")
st.caption(SLOGAN)

# ---------- State (ingatan selama sesi, dimuat dari file saat pertama dibuka) ----------
if "messages" not in st.session_state:
    st.session_state.messages = cli.load_chat()


# ---------- Fungsi bantu ----------
def pesan_error(e):
    if isinstance(e, AuthenticationError):
        return "API key salah atau tidak valid. Cek file .env kamu."
    if isinstance(e, RateLimitError):
        return "Terlalu banyak permintaan. Tunggu sebentar lalu coba lagi."
    if isinstance(e, APIConnectionError):
        return "Tidak bisa terhubung. Cek koneksi internetmu."
    if isinstance(e, APIStatusError):
        return f"Server API bermasalah (kode {e.status_code}). Coba lagi."
    return f"Terjadi error tak terduga: {e}"


def stream_reply(temperature, max_tokens):
    stream = cli.client.chat.completions.create(
        model=cli.MODEL,
        messages=cli.trimmed(st.session_state.messages),
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
    )
    for chunk in stream:
        if not chunk.choices:
            continue
        piece = chunk.choices[0].delta.content
        if piece:
            yield piece


def clear_todo_keys():
    """Hapus state checkbox lama supaya tampilan sinkron setelah tambah/hapus."""
    for k in list(st.session_state.keys()):
        if k.startswith("todo_"):
            del st.session_state[k]


def toggle_todo(i):
    todos = cli.load_todos()
    if i < len(todos):
        todos[i]["selesai"] = st.session_state[f"todo_{i}"]
        cli.save_todos(todos)


# ---------- Sidebar ----------
with st.sidebar:
    st.header("⚙️ Pengaturan")
    temperature = st.slider(
        "Temperature (kreativitas)", 0.0, 2.0, 0.7, 0.1,
        help="Rendah = konsisten, tinggi = lebih variatif",
    )
    max_tokens = st.slider("Panjang jawaban maks (token)", 200, 4000, 1500, 100)

    if st.button("🔄 Percakapan baru"):
        st.session_state.messages = cli.new_history()
        cli.save_chat(st.session_state.messages)
        st.rerun()

    st.download_button(
        "💾 Unduh riwayat (JSON)",
        data=json.dumps(st.session_state.messages[1:], ensure_ascii=False, indent=2),
        file_name="riwayat_kelarin.json",
        mime="application/json",
    )

    # ----- Daftar tugas -----
    st.header("✅ Daftar Tugas")
    todos = cli.load_todos()
    if not todos:
        st.caption("Belum ada tugas.")
    for i, t in enumerate(todos):
        c1, c2 = st.columns([5, 1])
        c1.checkbox(
            f"{t['tugas']} ({t['deadline']})",
            value=t["selesai"],
            key=f"todo_{i}",
            on_change=toggle_todo,
            args=(i,),
        )
        if c2.button("🗑️", key=f"hapus_{i}"):
            todos.pop(i)
            cli.save_todos(todos)
            clear_todo_keys()
            st.rerun()

    with st.form("form_tambah", clear_on_submit=True):
        nama = st.text_input("Tugas baru")
        dl = st.text_input("Deadline (opsional)", placeholder="2026-09-25 23:59")
        if st.form_submit_button("➕ Tambah"):
            if nama.strip():
                todos.append({"tugas": nama.strip(), "deadline": dl.strip() or "-", "selesai": False})
                cli.save_todos(todos)
                clear_todo_keys()
                st.rerun()
            else:
                st.warning("Nama tugas tidak boleh kosong.")

    # ----- Aksi cepat -----
    st.header("⚡ Aksi Cepat")
    if st.button("🗓️ Susun jadwal dari tugas"):
        menunggu = [t for t in todos if not t["selesai"]]
        if menunggu:
            daftar = "\n".join(f"- {t['tugas']} (deadline: {t['deadline']})" for t in menunggu)
            st.session_state.pending = (
                "Tolong susun prioritas dan jadwal pengerjaan untuk tugas-tugas berikut. "
                "Kalau informasi waktuku kurang, tanyakan dulu.\n" + daftar
            )
        else:
            st.warning("Belum ada tugas yang menunggu.")

    with st.expander("📝 Ringkas catatan"):
        catatan = st.text_area("Tempel catatanmu", height=150)
        if st.button("Ringkas"):
            if catatan.strip():
                st.session_state.pending = (
                    "Tolong ringkas catatan berikut jadi poin-poin inti:\n" + catatan.strip()
                )
            else:
                st.warning("Catatan masih kosong.")

    # ----- Statistik -----
    st.header("📊 Statistik")
    msgs = st.session_state.messages
    n_user = sum(1 for m in msgs if m["role"] == "user")
    n_bot = sum(1 for m in msgs if m["role"] == "assistant")
    selesai = sum(1 for t in todos if t["selesai"])
    st.write(f"Pesanmu: **{n_user}** | Balasan: **{n_bot}**")
    st.write(f"Tugas selesai: **{selesai} / {len(todos)}**")

# ---------- Tampilkan riwayat chat ----------
for m in st.session_state.messages[1:]:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# ---------- Input baru (kotak chat atau tombol aksi cepat) ----------
prompt = st.chat_input("Ketik pesanmu di sini...")
if not prompt:
    prompt = st.session_state.pop("pending", None)

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            reply = st.write_stream(stream_reply(temperature, max_tokens))
        except Exception as e:
            reply = None
            st.error(pesan_error(e))

        if reply and reply.strip():
            st.session_state.messages.append({"role": "assistant", "content": reply})
            cli.save_chat(st.session_state.messages)
            st.rerun()  # segarkan sidebar (statistik, unduhan)
        else:
            st.session_state.messages.pop()  # buang pesan user yang gagal
            if reply is not None:
                st.warning("Jawaban kosong (jatah token mungkin habis). Naikkan panjang jawaban maks.")