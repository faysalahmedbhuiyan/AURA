# AURA — Ubuntu Setup Guide (Fresh Machine → Auto-Protected)

এই guide follow করলে যেকোনো Ubuntu machine-এ AURA backend + security
monitor বসানো যাবে — একবার সেটআপ করলে, তারপর **শুধু login করলেই**
AURA automatically চালু হয়ে security protection দিতে শুরু করবে।
কোনো VS Code/কোড edit লাগবে না — নিচের command গুলো terminal-এ চালালেই হবে।

---

## ধাপ ১ — প্রাথমিক Package ইনস্টল

```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip git curl ufw network-manager libnotify-bin
```

- `ufw` — firewall control (IP block করার জন্য)
- `network-manager` — `nmcli` কমান্ড দেয় (wifi off করার জন্য)
- `libnotify-bin` — `notify-send` দেয় (desktop alert দেখানোর জন্য)

---

## ধাপ ২ — AURA কোড আনা

```bash
cd ~
git clone https://github.com/faysalahmedbhuiyan/AURA.git
cd AURA
git checkout checking
```

---

## ধাপ ৩ — Python venv ও Dependency

```bash
cd ~/AURA/backend
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## ধাপ ৪ — Ollama ইনস্টল ও Model তৈরি

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve &
cd ~/AURA/models
ollama create aura-brain -f aura-brain.modelfile
```

---

## ধাপ ৫ — `.env` ফাইল বসানো

```bash
cd ~/AURA/backend
nano .env
```

তোমার Windows machine-এর `.env`-এ যা যা আছে (`OLLAMA_MODEL`, `HF_TOKEN`, ইত্যাদি) — **paths গুলো শুধু Ubuntu-style-এ বদলে দাও**:

```dotenv
APP_NAME=AURA
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=aura-brain
SQLITE_DB_PATH=../database/aura.db
CHROMA_DB_PATH=../database/chroma
HF_TOKEN=তোমার_token
```

সেভ করো (`Ctrl+O`, `Enter`, `Ctrl+X`)।

---

## ধাপ ৬ — Sudo Permission (Security Feature-এর জন্য জরুরি)

Security monitor-কে root-ছাড়া নির্দিষ্ট কিছু কমান্ড চালানোর অনুমতি দিতে হবে:

```bash
sudo visudo -f /etc/sudoers.d/aura-security
```

এই লাইনটা লেখো (`your_username` জায়গায় নিজের username বসাও, `whoami` কমান্ড দিয়ে চেক করে নাও):

```
your_username ALL=(ALL) NOPASSWD: /usr/sbin/ufw, /usr/sbin/shutdown
```

সেভ করো (`Ctrl+O`, `Enter`, `Ctrl+X`)। SSH log পড়ার জন্য নিজেকে `adm` group-এ যোগ করো:

```bash
sudo usermod -aG adm $USER
```

⚠️ এই ধাপের পর **একবার log out করে আবার log in করো** যাতে group পরিবর্তন কার্যকর হয়।

---

## ধাপ ৭ — systemd Service বানানো (এটাই "auto-start on login" এর মূল অংশ)

```bash
sudo nano /etc/systemd/system/aura-backend.service
```

এই content বসাও (`your_username` আর path গুলো নিজের অনুযায়ী বদলাও):

```ini
[Unit]
Description=AURA Backend with Security Monitor
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/home/your_username/AURA/backend
ExecStart=/home/your_username/AURA/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=on-failure
RestartSec=5
Environment=DISPLAY=:0

[Install]
WantedBy=default.target
```

(`Environment=DISPLAY=:0` লাইনটা জরুরি — এটা ছাড়া `notify-send` desktop alert কাজ করবে না)

সেভ করো, তারপর:

```bash
sudo systemctl daemon-reload
sudo systemctl enable aura-backend
sudo systemctl start aura-backend
```

`enable` command-টাই মূল জাদু — এর মানে **প্রতিবার Ubuntu চালু/login হলে AURA backend নিজে থেকেই চালু হয়ে যাবে**, তোমাকে কিছু করতে হবে না।

---

## ধাপ ৮ — যাচাই করো সব ঠিক আছে কিনা

```bash
sudo systemctl status aura-backend
```

`active (running)` দেখানোর কথা। Log দেখতে:

```bash
sudo journalctl -u aura-backend -f
```

এখানে `"AURA security monitor auto-started."` লাইনটা দেখলে বুঝবে security protection নিজে থেকেই চালু হয়ে গেছে।

Browser/curl দিয়ে confirm করো:

```bash
curl http://127.0.0.1:8000/api/v1/security/status
```

`"running": true` দেখানোর কথা।

---

## ধাপ ৯ — Test করো (shutdown ছাড়াই, safe ভাবে)

অন্য একটা device থেকে (phone/অন্য কম্পিউটার) তোমার Ubuntu machine-এর IP তে একটা basic port scan চালাও:

```bash
# অন্য মেশিনে (nmap ইনস্টল থাকলে)
nmap <তোমার-ubuntu-machine-এর-IP>
```

তোমার Ubuntu-তে একটা desktop notification পপ-আপ হওয়ার কথা। এটা দেখলে বুঝবে detection কাজ করছে।

---

## রোজকার ব্যবহার — তোমার জন্য যা মনে রাখা দরকার

| তুমি কী করো                        | AURA কী করে                                                                                   |
| ---------------------------------- | --------------------------------------------------------------------------------------------- |
| Ubuntu-তে password দিয়ে login করো | systemd service নিজে থেকেই AURA backend চালু করে দেয়                                         |
| কিছুই আলাদা করে চালাতে হয় না      | Security monitor নিজে থেকেই scanning শুরু করে (৯ নম্বর ধাপে যোগ করা auto-start hook-এর কারণে) |
| Normal কাজ চালিয়ে যাও             | Background-এ প্রতি ১৫ সেকেন্ডে network connection scan হতে থাকে                               |
| কেউ attack করার চেষ্টা করলে        | Desktop notification পাবে, উচ্চ-ঝুঁকিতে IP block + wifi off, চরম ঝুঁকিতে shutdown             |

---

## যদি কখনো বন্ধ করতে চাও

```bash
sudo systemctl stop aura-backend      # সাময়িক বন্ধ
sudo systemctl disable aura-backend   # auto-start বন্ধ করো (boot এ আর চালু হবে না)
```

---

## মনে রাখতে হবে

- **শুরুতে shutdown feature সাময়িকভাবে বন্ধ রাখো** (আগে বলা হয়েছে) — কয়েকদিন শুধু alert/log দেখে threshold ঠিক আছে কিনা যাচাই করে নাও, তারপর সক্রিয় করো
- যদি কোনো নতুন Ubuntu machine-এ আবার বসাতে চাও, শুধু ধাপ ১-৮ আবার করলেই হবে — কোড একই থাকবে, শুধু OS-level setup repeat করতে হবে
