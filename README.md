# 📝 Kelarin - Atur Waktumu, Kelarin Tugasmu!
Created by: Alifia Annisa Rahma | 3324600058

## 1. Tema dan Konsep
Topik yang diambil adalah terkait Asisten Produktivitas Mahasiswa.
Kelarin merupakan chatbot asisten produktivitas yang ditujukan untuk mahasiswa dalam membantu merencanakan dan mengatur pengerjaan tugas. 
Berikut beberapa hal yang akan dilakukan oleh chatbot ini, antara lain: 
1. Menentukan prioritas tugas 
2. Menyusun jadwal pengerjaan
3. Memecah tugas besar menjadi langkah kecil
4. Meringkas catatan kuliah
Kelarin tidak mengerjakan tugas untuk menggantikan kewajiban pengguna, melainkan membantu pengguna dalam merencanakan dan menyelesaikannya tugasnya sendiri.

### Fitur
- System prompt bertema produktivitas (peran, alur, format jawaban, batasan)
- Conversation history: bot mengingat konteks, dan dibatasi 20 pesan terakhir agar hemat token
- Penanganan error (API key salah, koneksi putus, rate limit, jawaban kosong)
- Perintah khusus: `exit`, `clear`, dan perintah `/` lainnya (tabel di bawah)
- **Bonus:** streaming, tampilan web Streamlit, simpan dan muat riwayat otomatis,
  daftar tugas tersimpan di file, statistik, kontrol temperature dan panjang jawaban

## 2. Cara Menjalankan Chatbot
1. Clone repo dan masuk foldernya
   ```bash
   git clone https://github.com/ayyalifians/chatbot-kelarin.git
   cd chatbot-kelarin
   ```
2. Buat dan aktifkan venv
   ```bash
   python -m venv venv
   venv\Scripts\activate          # Windows
   source venv/bin/activate       # Mac/Linux
   ```
3. Install library, `pip install -r requirements.txt`
4. Siapkan API key: salin `.env.example` menjadi `.env`, lalu isi `GROQ_API_KEY`
   (buat key di https://console.groq.com/keys). Nama model diatur lewat `GROQ_MODEL`.
5. Jalankan versi console:
   ```bash
   python cli.py
   ```
6. Atau jalankan versi web:
   ```bash
   streamlit run app.py
   ```

> Jangan menjalankan versi console dan web bersamaan, karena keduanya memakai file riwayat yang sama.

### Perintah di Console

| Perintah | Fungsi |
|---|---|
| `exit` / `/exit` | Keluar |
| `clear` / `/reset` | Mulai percakapan baru |
| `/tambah tugas \| deadline` | Tambah tugas (deadline opsional) |
| `/todo` | Lihat daftar tugas |
| `/selesai nomor` | Tandai tugas selesai |
| `/hapus nomor` | Hapus tugas |
| `/jadwal` | Susun jadwal dari tugas yang belum selesai |
| `/ringkas` | Ringkas catatan yang ditempel |
| `/temp angka` | Atur temperature (0-2) |
| `/panjang angka` | Atur panjang jawaban maksimal (token) |
| `/stats` | Statistik percakapan dan tugas |
| `save` / `/save` | Simpan arsip salinan riwayat |
| `/load` | Muat arsip riwayat terbaru |
| `help` / `/help` | Bantuan |

Daftar perintah: /help /tambah /todo /selesai /jadwal /ringkas /stats /save /load /reset /exit

## 3. Contoh Percakapan
(screenshot terlampir dalam folder screenshots/)
- Percobaan chat 1: Menampilkan fitur-fitur untuk melakukan eksekusi perintah
- Percobaan chat 2: Mencoba prompt untuk berkeluh kesah dan menyampaikan adanya 2 tugas dengan deadline yang sama, kemudian bot membantu membuatkan langkah - langkah kecil untuk penyelesaian tugas dan disertai jadwal prioritas
- Percobaan chat 3: Mencoba menanyakan bantuan untuk mengerjakan tugas, chatbot menuliskan bukan ranahnya namun dia bisa membantu membuat kerangka tugasnya
- Percobaan chat 4: Memberitahukan tugas 1 selesai dikerjakan agar bisa update list tugas apa yang belum dikerjakan
- Percobaan chat 5: keluar dari chat

## 4. Struktur Kode
```
chatbot-kelarin/
├── prompts.py        # nama, slogan, dan system prompt
├── cli.py            # versi console (logika utama)
├── app.py            # versi web Streamlit (memakai ulang fungsi dari cli.py)
├── requirements.txt
├── .env.example      # contoh format API key (.env asli tidak di-upload)
├── .gitignore
├── screenshots/
└── history/          # dibuat otomatis, tidak di-upload (percakapan.json, todo.json)
```

| Bagian | Fungsi |
|---|---|
| `SYSTEM_PROMPT` (`prompts.py`) | Peran, alur, format jawaban, dan batasan Kelarin |
| `new_history()`, `trimmed()` | Membuat history dan membatasi pesan yang dikirim ke API |
| `ask_llm()` | Memanggil Groq API dengan streaming |
| `send()` | Menambah pesan, memanggil API, menangani error, membuang pesan user jika gagal |
| `save_chat()`, `load_chat()` | Simpan dan muat percakapan otomatis |
| `load_todos()`, `add_todo()`, dll. | Mengelola daftar tugas di `todo.json` |
| `todo_context()` | Menyisipkan tanggal dan daftar tugas terbaru ke API |
| `handle_command()` | Memproses perintah khusus |

### Alur

```
input → (perintah? jalankan) → tambah ke messages → kirim ke API → tampil bertahap → simpan
```

### Pengelolaan history
LLM tidak punya memori antar-request, sehingga seluruh riwayat (`messages`)
dikirim ulang setiap giliran. Agar token tidak cepat habis, hanya 20 pesan terakhir
yang dikirim. Percakapan disimpan otomatis ke `history/percakapan.json` dan
dimuat kembali saat program dibuka.

### Penanganan error
Setiap panggilan API dibungkus `try/except`. Jika gagal, muncul pesan yang
jelas, pesan pengguna dibuang dari history agar tidak rusak, dan program tetap berjalan.

## Analisis dan Keterbatasan
- **Status tugas dan konteks LLM.** Pada pengujian awal, bot sempat menyebut jumlah
  tugas yang belum selesai secara keliru karena jawaban lama di riwayat lebih
  berpengaruh daripada data terbaru di system prompt. Perbaikannya: data tugas terbaru
  (beserta hitungan) ditempel di pesan pengguna terakhir pada setiap panggilan API.
  Untuk data yang harus akurat, gunakan `/todo`.
- **LLM hanya menghasilkan teks.** Kalimat biasa seperti "tolong catat tugasku" tidak
  menyimpan apa pun; penyimpanan dilakukan lewat perintah `/tambah`. Bot diarahkan agar
  tidak mengaku sudah menyimpan.
- **Pengembangan lanjutan:** function calling agar LLM dapat memanggil fungsi to-do
  langsung dari kalimat biasa.

## Keamanan API Key
API key disimpan di `.env` yang masuk `.gitignore`, sehingga tidak ikut ke repository.
`.env.example` hanya berisi contoh.

## Penggunaan AI
- Dibantu AI:
  1. Kerangka Awal Script `cli.py` dan `app.py`
  2. Draf awal system prompt
  3. Bantuan debugging code
  4. Pengembangan draf README
- Dikerjakan sendiri:
  1. Penentuan tema, topik yang diambil, nama aplikasi dan slogan
  2. Penentuan fokus, tujuan, dan batasan pertanyaan pengguna pada chatbot (prompting sesuai file prompts.py)
  3. Persiapan environment, repo GitHub, dan API key
  4. Konsep pengujian chatbot
  5. Penulisan dan isi penjelasan README
  6. Gambaran kasar ui chatbot via streamlit
