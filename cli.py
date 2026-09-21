import os
import sys
import json
from datetime import datetime
from getpass import getpass

from dotenv import load_dotenv
from groq import (
    Groq,
    APIConnectionError,
    RateLimitError,
    AuthenticationError,
    APIStatusError,
)

from prompts import SYSTEM_PROMPT, APP_NAME, SLOGAN

# PENGATURAN
load_dotenv()
API_KEY = os.getenv("GROQ_API_KEY")
if not API_KEY:
    # Sama seperti contoh di modul: kalau .env belum ada, minta input tersembunyi
    API_KEY = getpass("Masukkan GROQ_API_KEY kamu (input tersembunyi): ").strip()
if not API_KEY:
    sys.exit("GROQ_API_KEY tidak ditemukan. Isi di file .env atau ketik saat diminta.")

client = Groq(api_key=API_KEY)
MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
MAX_HISTORY = 20  # jumlah pesan terakhir yang dikirim ke API (hemat token)

# Bisa diubah pengguna lewat /temp dan /panjang
settings = {"temperature": 0.7, "max_tokens": 1500}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_DIR = os.path.join(BASE_DIR, "history")
TODO_FILE = os.path.join(HISTORY_DIR, "todo.json")
CHAT_FILE = os.path.join(HISTORY_DIR, "percakapan.json")
os.makedirs(HISTORY_DIR, exist_ok=True)

# Kata tunggal seperti di modul (exit, clear, save) dianggap sebagai perintah
ALIAS = {
    "exit": "/exit",
    "quit": "/exit",
    "clear": "/reset",
    "reset": "/reset",
    "save": "/save",
    "help": "/help",
}

# TO-DO LIST (disimpan ke file)
def load_todos():
    if os.path.exists(TODO_FILE):
        try:
            with open(TODO_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except (json.JSONDecodeError, OSError):
            print("[Peringatan] todo.json rusak, memakai daftar kosong.")
    return []

def save_todos(todos):
    with open(TODO_FILE, "w", encoding="utf-8") as f:
        json.dump(todos, f, ensure_ascii=False, indent=2)

def parse_nomor(arg, todos):
    """Ubah teks nomor jadi indeks list. None kalau tidak valid."""
    try:
        idx = int(arg) - 1
    except ValueError:
        return None
    if 0 <= idx < len(todos):
        return idx
    return None

def add_todo(arg):
    tugas, _, deadline = arg.partition("|")
    tugas = tugas.strip()
    if not tugas:
        print("Format: /tambah nama tugas | deadline (deadline boleh dikosongkan)")
        return
    todos = load_todos()
    todos.append({"tugas": tugas, "deadline": deadline.strip() or "-", "selesai": False})
    save_todos(todos)
    print(f"Ditambahkan: {tugas} 📝")

def show_todos():
    todos = load_todos()
    if not todos:
        print("Daftar tugas masih kosong. Tambah dengan /tambah nama tugas | deadline")
        return
    print("\nDaftar tugasmu:")
    for i, t in enumerate(todos, 1):
        tanda = "x" if t["selesai"] else " "
        print(f"  {i}. [{tanda}] {t['tugas']} (deadline: {t['deadline']})")
    print()

def finish_todo(arg):
    todos = load_todos()
    idx = parse_nomor(arg, todos)
    if idx is None:
        print("Format: /selesai nomor  (lihat nomornya dengan /todo)")
        return
    todos[idx]["selesai"] = True
    save_todos(todos)
    print(f"Mantap, selesai: {todos[idx]['tugas']} 🎉")

def delete_todo(arg):
    todos = load_todos()
    idx = parse_nomor(arg, todos)
    if idx is None:
        print("Format: /hapus nomor  (lihat nomornya dengan /todo)")
        return
    removed = todos.pop(idx)
    save_todos(todos)
    print(f"Dihapus: {removed['tugas']}")

# HISTORY PERCAKAPAN
def new_history():
    """Riwayat baru: hanya berisi system prompt."""
    return [{"role": "system", "content": SYSTEM_PROMPT}]

def todo_context():
    """Ringkasan tanggal + daftar tugas terkini, lengkap dengan hitungan."""
    sekarang = datetime.now().strftime("%Y-%m-%d %H:%M")
    teks = f"Tanggal dan waktu sekarang: {sekarang}\n"
    todos = load_todos()
    if not todos:
        return teks + "DAFTAR TUGAS PENGGUNA: (masih kosong)"
    belum = sum(1 for t in todos if not t["selesai"])
    teks += (
        f"DAFTAR TUGAS PENGGUNA: total {len(todos)}, "
        f"belum selesai {belum}, selesai {len(todos) - belum}\n"
    )
    for i, t in enumerate(todos, 1):
        status = "SELESAI" if t["selesai"] else "BELUM SELESAI"
        teks += f"{i}. {t['tugas']} (deadline: {t['deadline']}) - {status}\n"
    return teks.rstrip()


def trimmed(messages):
    """System prompt + N pesan terakhir.
    Data tugas terbaru ditempel di pesan user paling akhir (hanya di salinan
    yang dikirim ke API, tidak disimpan ke history) supaya tidak kalah oleh
    jawaban lama di riwayat chat."""
    system = {"role": "system", "content": messages[0]["content"]}
    recent = [dict(m) for m in messages[1:][-MAX_HISTORY:]]
    if recent and recent[-1]["role"] == "user":
        recent[-1]["content"] += (
            "\n\n[DATA TERBARU DARI PROGRAM - gunakan ini untuk status tugas; "
            "jika jawabanmu sebelumnya berbeda, data ini yang benar]\n"
            + todo_context()
        )
    return [system] + recent

def save_chat(messages):
    """Simpan percakapan saat ini (dipanggil otomatis setiap giliran)."""
    try:
        with open(CHAT_FILE, "w", encoding="utf-8") as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
    except OSError as e:
        print(f"[Peringatan] Riwayat gagal disimpan: {e}")

def load_chat():
    """Muat percakapan terakhir kalau ada, kalau tidak buat yang baru."""
    if os.path.exists(CHAT_FILE):
        try:
            with open(CHAT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list) and data and data[0].get("role") == "system":
                # pakai system prompt terbaru, kalau prompts.py pernah diubah
                data[0] = {"role": "system", "content": SYSTEM_PROMPT}
                return data
        except (json.JSONDecodeError, OSError, AttributeError):
            print("[Peringatan] Riwayat lama rusak, memulai percakapan baru.")
    return new_history()

def show_recent(messages, n=4):
    """Tampilkan beberapa pesan terakhir supaya pengguna tahu konteksnya."""
    recent = messages[1:][-n:]
    if not recent:
        return
    print(f"\nRiwayat sebelumnya dimuat ({len(messages) - 1} pesan). Terakhir:")
    for m in recent:
        nama = "Kamu" if m["role"] == "user" else APP_NAME
        teks = m["content"].replace("\n", " ")
        if len(teks) > 120:
            teks = teks[:120] + "..."
        print(f"  {nama}: {teks}")

# PANGGILAN KE LLM
def ask_llm(messages):
    """Kirim ke API dengan streaming, kembalikan teks jawaban lengkap."""
    stream = client.chat.completions.create(
        model=MODEL,
        messages=trimmed(messages),
        temperature=settings["temperature"],
        max_tokens=settings["max_tokens"],
        stream=True,
    )
    full = ""
    for chunk in stream:
        if not chunk.choices:
            continue
        piece = chunk.choices[0].delta.content
        if piece:
            print(piece, end="", flush=True)
            full += piece
    print()
    return full

def send(messages, text):
    """Kirim satu pesan user ke LLM dengan penanganan error.
    Kalau gagal, pesan user dibuang dari history agar history tetap rapi."""
    messages.append({"role": "user", "content": text})
    try:
        print(f"{APP_NAME}: ", end="", flush=True)
        reply = ask_llm(messages)
        if reply.strip():
            messages.append({"role": "assistant", "content": reply})
            save_chat(messages)
            return True
        print("[Peringatan] Jawaban kosong (jatah token mungkin habis). "
              "Coba /panjang 2000 lalu kirim ulang pesanmu.")
    except AuthenticationError:
        print("\n[Error] API key salah atau tidak valid. Cek file .env kamu.")
    except RateLimitError:
        print("\n[Error] Terlalu banyak permintaan. Tunggu sebentar lalu coba lagi.")
    except APIConnectionError:
        print("\n[Error] Tidak bisa terhubung. Cek koneksi internetmu.")
    except APIStatusError as e:
        print(f"\n[Error] Server API bermasalah (kode {e.status_code}). Coba lagi.")
    except KeyboardInterrupt:
        print("\n[Dibatalkan]")
    except Exception as e:
        print(f"\n[Error tak terduga] {e}")
    messages.pop()
    return False

# PERINTAH KHUSUS
def show_help():
    print(
        "\nPerintah:\n"
        "  /help               tampilkan bantuan\n"
        "  /tambah tugas | dl  tambah tugas ke daftar (deadline opsional)\n"
        "  /todo               lihat daftar tugas\n"
        "  /selesai nomor      tandai tugas selesai\n"
        "  /hapus nomor        hapus tugas dari daftar\n"
        "  /jadwal             susun jadwal dari tugas yang belum selesai\n"
        "  /ringkas            ringkas catatan yang kamu tempel\n"
        "  /temp angka         atur temperature 0-2 (tanpa angka: lihat nilai)\n"
        "  /panjang angka      atur panjang jawaban maks dalam token\n"
        "  /stats              statistik percakapan dan tugas\n"
        "  /save               simpan salinan arsip riwayat\n"
        "  /load               muat arsip riwayat terbaru\n"
        "  /reset (atau clear) mulai percakapan baru\n"
        "  /exit  (atau exit)  keluar\n"
        "\nRiwayat percakapan dan daftar tugas tersimpan otomatis.\n"
    )

def make_schedule(messages):
    pending = [t for t in load_todos() if not t["selesai"]]
    if not pending:
        print("Belum ada tugas yang menunggu. Tambah dulu dengan /tambah.")
        return
    daftar = "\n".join(f"- {t['tugas']} (deadline: {t['deadline']})" for t in pending)
    send(
        messages,
        "Tolong susun prioritas dan jadwal pengerjaan untuk tugas-tugas berikut. "
        "Kalau informasi waktuku kurang, tanyakan dulu.\n" + daftar,
    )

def summarize_notes(messages):
    print("Tempel catatanmu, lalu tekan Enter dua kali untuk selesai")
    print("(hindari baris kosong di tengah teks):")
    lines = []
    try:
        while True:
            line = input()
            if line == "":
                break
            lines.append(line)
    except (KeyboardInterrupt, EOFError):
        print("\n[Dibatalkan]")
        return
    text = "\n".join(lines).strip()
    if not text:
        print("Tidak ada teks yang ditempel.")
        return
    send(messages, "Tolong ringkas catatan berikut jadi poin-poin inti:\n" + text)

def set_temperature(arg):
    if not arg:
        print(f"Temperature saat ini: {settings['temperature']}")
        return
    try:
        value = float(arg)
        if not 0 <= value <= 2:
            raise ValueError
    except ValueError:
        print("Format: /temp angka antara 0 dan 2, contoh: /temp 0.5")
        return
    settings["temperature"] = value
    print(f"Temperature diubah menjadi {value}")

def set_max_tokens(arg):
    if not arg:
        print(f"Panjang jawaban maks saat ini: {settings['max_tokens']} token")
        return
    try:
        value = int(arg)
        if not 200 <= value <= 4000:
            raise ValueError
    except ValueError:
        print("Format: /panjang angka antara 200 dan 4000, contoh: /panjang 2000")
        return
    settings["max_tokens"] = value
    print(f"Panjang jawaban maks diubah menjadi {value} token")

def show_stats(messages):
    user_msgs = [m for m in messages if m["role"] == "user"]
    bot_msgs = [m for m in messages if m["role"] == "assistant"]
    avg = (
        sum(len(m["content"]) for m in user_msgs) / len(user_msgs)
        if user_msgs else 0
    )
    todos = load_todos()
    selesai = sum(1 for t in todos if t["selesai"])
    print(
        f"\nJumlah pesanmu           : {len(user_msgs)}"
        f"\nJumlah balasan           : {len(bot_msgs)}"
        f"\nRata-rata panjang pesanmu: {avg:.0f} karakter"
        f"\nTugas selesai / total    : {selesai} / {len(todos)}"
        f"\nTemperature              : {settings['temperature']}"
        f"\nPanjang jawaban maks     : {settings['max_tokens']} token\n"
    )

def save_history(messages):
    name = datetime.now().strftime("riwayat_%Y%m%d_%H%M%S.json")
    path = os.path.join(HISTORY_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)
    print(f"Arsip riwayat disimpan di {path}")

def load_history():
    files = sorted(f for f in os.listdir(HISTORY_DIR) if f.startswith("riwayat_"))
    if not files:
        print("Belum ada arsip riwayat. Buat dulu dengan /save.")
        return None
    path = os.path.join(HISTORY_DIR, files[-1])  # yang terbaru
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not (isinstance(data, list) and data and data[0].get("role") == "system"):
            raise ValueError("format arsip tidak sesuai")
    except (json.JSONDecodeError, OSError, ValueError, AttributeError) as e:
        print(f"[Error] Arsip tidak bisa dimuat: {e}")
        return None
    print(f"Memuat {path} ({len(data) - 1} pesan)")
    return data

def handle_command(cmd, arg, messages):
    """Kembalikan (messages_baru, lanjut_atau_tidak)."""
    if cmd == "/exit":
        print(f"{APP_NAME}: Semangat ya, sampai jumpa! 👋")
        return messages, False
    if cmd in ("/reset", "/clear"):
        print(f"{APP_NAME}: Oke, kita mulai dari awal ya! 📝")
        fresh = new_history()
        save_chat(fresh)
        return fresh, True
    if cmd == "/help":
        show_help()
    elif cmd == "/tambah":
        add_todo(arg)
    elif cmd == "/todo":
        show_todos()
    elif cmd == "/selesai":
        finish_todo(arg)
    elif cmd == "/hapus":
        delete_todo(arg)
    elif cmd == "/jadwal":
        make_schedule(messages)
    elif cmd == "/ringkas":
        summarize_notes(messages)
    elif cmd == "/temp":
        set_temperature(arg)
    elif cmd == "/panjang":
        set_max_tokens(arg)
    elif cmd == "/stats":
        show_stats(messages)
    elif cmd == "/save":
        save_history(messages)
    elif cmd == "/load":
        data = load_history()
        if data:
            save_chat(data)
            return data, True
    else:
        print("Perintah tidak dikenal. Ketik /help untuk daftar perintah.")
    return messages, True

# PROGRAM UTAMA
def main():
    messages = load_chat()
    print("=" * 55)
    print(f"📝 {APP_NAME} - {SLOGAN}")
    print("Ketik /help untuk melihat perintah, exit untuk keluar.")
    print("=" * 55)
    show_recent(messages)

    while True:
        try:
            user_input = input("\nKamu    : ").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{APP_NAME}: Sampai jumpa! 👋")
            break

        if not user_input:
            print("Silakan ketik pesan atau perintah (/help untuk bantuan).")
            continue

        # exit / clear / save / help (satu kata) dianggap perintah, seperti di modul
        if user_input.lower() in ALIAS:
            user_input = ALIAS[user_input.lower()]

        if user_input.startswith("/"):
            cmd, _, arg = user_input.partition(" ")
            try:
                messages, keep_going = handle_command(cmd.lower(), arg.strip(), messages)
            except Exception as e:
                print(f"[Perintah gagal: {e}]")
                keep_going = True
            if not keep_going:
                break
            continue

        send(messages, user_input)

if __name__ == "__main__":
    main()