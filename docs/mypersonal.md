mypersonal.md:
AURA Backend Start করার SOP (Standard Operating Procedure)
প্রতিবার VS Code বন্ধ করে আবার খুললে এই ধাপগুলো follow করবেন:
ধাপ ১ — VS Code এ Terminal খুলুন
Ctrl + ` (backtick)
ধাপ ২ — Backend ফোল্ডারে যান
powershellcd D:\AURA\backend
ধাপ ৩ — venv Activate করুন
powershell : .\venv\Scripts\Activate.ps1
টার্মিনালে (venv) দেখালে বুঝবেন সফল হয়েছে।
ধাপ ৪ — Server Start করুন
powershell : uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
এটা দেখালে server ready:
INFO: Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
ধাপ ৫ — Browser এ verify করুন
http://127.0.0.1:8000/api/v1/health
http://127.0.0.1:8000/docs

AI Relistic pic banate ram kom tai eta vs code e ba calu rekhe baki sob off rekhe
ei code calate hobe:
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/image/generate" -Method POST -ContentType "application/json" -Body '{"prompt": "a young Bangladeshi boy standing outside kyungpook National university gate, photorealistic, natural daylight", "quality": "realistic"}'

Coder hisebe subagent ke sikhate eta use korbo prompt er age
teach sub agent expert-software-engineer-who-writes-clea-d7c49d :

AURA/
├── backend/ ← FastAPI backend (Phase 0 ✅)
├── frontend/ ← React + Electron (upcoming)
├── brain/ ← LLM integration (upcoming)
├── memory/ ← ChromaDB + SQLite (upcoming)
├── voice/ ← Whisper + Piper (upcoming)
├── docs/ ← All documentation
└── database/ ← Local databases

aura ke diye ki ki kaj korabo tar list:

1. aura amar voice e calu hobe. ami voice dile se o amake voice diye ba ami caile se likhe o amake ans dite parbe.
2. aura online theke altime informetion collect korte thakbe but segulo confirm korbe na jotokhon na ami confirm kori.
3. aura amar permition e kono ekta topic er upor onek knowledge collect korbe online seorce theke.
4. aura ke ami bangla ba banglish e likhle o se seta bangla te translate kore seivabe kaj korbe.
   mane onnanno AI er moto se banglish bujbe.
5. aura sob question er answer knub short e real ta dibe.
6. se amar pc te full access pabe and je kno file access korte parbe and seta read kore knowledge gain korte parbe.
7. aura ke ami jekono file dite parbe se seta read kore tar kache memorized korte parbe.
8. aura nijer code develop korte parbe amar order e.
9. ami take jodi kono code dei ba kono project dei seta thik kore korte parbe and chat histry se mone rakhbe and amake displayte show korte parbe. jemonta amra Chatgpt te dekhi pase side bar e chat histry thake sevabe.
10. in feature se AI video , AI image esob generate korte parbe. amar instraction dekhe.
11. aura onekta jarves er moto kaj korbe nije noje online theke coding business etc sikhbe and seta confirm ami korle permanent knowledge e rakhbe.

aura r jonne eta token ja video er jonne use hobe: YOUR_HUGGINGFACE_TOKEN_HERE
ja ekhan theke neya https://huggingface.co/settings/tokens

# AURA — এখন পর্যন্ত কী কী করতে পারে ও কী পারে না

**তৈরি হয়েছে:** ২৭ জুলাই, ২০২৬ | **Branch:** `checking`

---

## AURA আসলে কী

AURA একটা লোকাল-ফার্স্ট (local-first) পার্সোনাল AI OS assistant — মানে এর
মূল বুদ্ধিমত্তা (Ollama দিয়ে চালানো `aura-brain` LLM), memory, আর data
সব তোমার নিজের কম্পিউটারেই (D:\AURA) থাকে, কোনো বাইরের cloud এ যায় না।

---

## ✅ যা এখন কাজ করে (Working Features)

### চ্যাট ও কথোপকথন

- Text চ্যাট (বাংলা ও ইংরেজি) — Ollama এর `aura-brain` মডেল দিয়ে
- Conversation history — সব পুরনো চ্যাট sidebar এ সংরক্ষিত থাকে, চ্যাট delete করা যায়
- Deterministic intent detection — কিছু নির্দিষ্ট command (search, save, delete,
  ছবি বানানো ইত্যাদি) সরাসরি code দিয়ে ধরা হয়, LLM কে জিজ্ঞেস না করেই কাজ হয়ে যায়

### মেমরি সিস্টেম (৪ ধরনের)

- **Personal Memory** — তোমার ব্যক্তিগত পছন্দ, তথ্য, অভ্যাস
- **Knowledge Base** — যাচাই-করা তথ্য (web search বা ফাইল থেকে আসা)
- **Decision Memory** — গুরুত্বপূর্ণ সিদ্ধান্তের রেকর্ড
- **Learning Queue** — নতুন কিছু শেখার আগে **তোমার কনফার্মেশন** লাগে (স্বয়ংক্রিয়ভাবে
  কিছু "মুখস্থ" করে ফেলে না, তোমাকে জিজ্ঞেস করে আগে)
- সব কিছু ChromaDB (vector database) দিয়ে semantic search করা যায়

### ডকুমেন্ট শেখা (এটাই তোমার "business docs শেখানো"-র জন্য দরকার!)

- PDF, DOCX, ছবি (OCR সহ) আপলোড করে AURA কে পড়ানো যায়
- দুই মোড:
  - **Stage** (`/ingestion/stage`) — সাময়িক, শুধু ওই কথোপকথনে ব্যবহারের জন্য, স্থায়ীভাবে সেভ হয় না যতক্ষণ না তুমি "save it" বলো
  - **Upload** (`/ingestion/upload`) — সরাসরি pending queue তে যায়, পরে confirm করলে স্থায়ীভাবে জ্ঞানভাণ্ডারে যোগ হয়
- File Vault — স্থায়ীভাবে সেভ করা ফাইল সব এক জায়গায় দেখা যায়

### ভয়েস (কোডে আছে, কিন্তু তুমি এখন বন্ধ রেখেছ)

- Speech-to-Text (faster-whisper) ও Text-to-Speech (Piper) কোড সম্পূর্ণ তৈরি,
  বাংলা ভয়েস সাপোর্ট আছে বলে docs এ লেখা
- **তুমি নিজে সিদ্ধান্ত নিয়েছ:** আপাতত ভয়েস + বহু-ভাষা (হিন্দি, কোরিয়ান) ফিচার বন্ধ
  রাখছ, শুধু বাংলা/ইংরেজি টেক্সট চ্যাট ব্যবহার করছ — এটা ঠিক আছে, কোড নষ্ট হয়নি,
  শুধু ব্যবহার করছ না

### ছবি তৈরি (Tier 5 — আজই শেষ হয়েছে)

- SD Turbo মডেল দিয়ে লোকাল image generation (CPU এ, ~৮০-১২০ সেকেন্ড/ছবি)
- চ্যাটে সরাসরি লিখে ("generate an image of...") ছবি বানানো যায়, ছবি চ্যাটেই দেখা যায়
- **সীমাবদ্ধতা:** GPU (Intel Iris Xe) দিয়ে করা যাচ্ছে না এখনো (VRAM কম পড়ে), তাই ধীর

### Self-Improvement সিস্টেম (Phase 8-11)

- **Self Review** — নিজের কোড quality চেক করে, সমস্যা খুঁজে বের করে (শুধু Python, .py ফাইল)
- **Self Improvement Planner** — কোনো পরিবর্তনের আগে পুরো plan বানায় (কী বদলাবে,
  কী ঝুঁকি, কী লাভ)
- **Safe Self Modification** — **কখনোই তোমার অনুমতি ছাড়া নিজের কোড বদলায় না।**
  Change করার আগে automatic backup নেয়। কিছু protected ফাইল (main.py, .env)
  কখনোই এই সিস্টেম দিয়ে বদলানো যায় না
- **Rollback System** — Git-ভিত্তিক, যেকোনো পরিবর্তন ফিরিয়ে আনা যায়

### এজেন্ট (Agents)

- File Management Agent — ফাইল খোঁজা, organize করা
- System Control Agent — সিস্টেম তথ্য, নিয়ন্ত্রণ
- Web Search Agent — SearXNG দিয়ে ইন্টারনেট সার্চ

### অন্যান্য

- Development Journal — AURA নিজের কাজের ইতিহাস লিখে রাখে
- Coding Mentor Mode — পরিকল্পনায় আছে (এখনো শুরু হয়নি)

---

## ❌ যা এখনো নেই / অসম্পূর্ণ (Limitations)

| বিষয়                                  | অবস্থা                                                              |
| -------------------------------------- | ------------------------------------------------------------------- |
| Video generation                       | শুরুই হয়নি (cloud API লাগবে, planning পর্যায়ে)                    |
| GPU দিয়ে ছবি তৈরি                     | চেষ্টা হয়েছে, কাজ করেনি (VRAM 3.9GB যথেষ্ট না), তাই CPU-only       |
| Coding Mentor Mode                     | Documented আছে, কোনো কোড লেখা হয়নি                                 |
| Goal Manager                           | Documented আছে, কোনো কোড লেখা হয়নি                                 |
| Project Understanding Engine           | Documented আছে, কোনো কোড লেখা হয়নি                                 |
| Self Review                            | শুধু Python — frontend JS/JSX/CSS বিশ্লেষণ করে না                   |
| Self-modification পরীক্ষা              | কোড বদলানোর পর automated test চালানো এখনো নেই                       |
| Task automation agent                  | পরিকল্পনায়, তৈরি হয়নি                                             |
| Web browsing agent                     | পরিকল্পনায়, তৈরি হয়নি                                             |
| Multi-language ভয়েস (হিন্দি/কোরিয়ান) | কোড আছে কিন্তু বর্তমানে ব্যবহার বন্ধ রাখা হয়েছে (তোমার সিদ্ধান্তে) |

---

## নিরাপত্তা সংক্রান্ত মৌলিক নীতি (এগুলো বদলানো উচিত না)

- AURA কখনো নিজের কোড **নিঃশব্দে** বদলায় না — সবসময় তোমার approval লাগে
- নতুন কিছু "শেখার" আগে (Learning Queue থেকে confirm) তোমার অনুমতি লাগে
- Protected files (main.py, .env, modification system নিজেই) কখনো auto-modify হয় না
- সব change এর আগে backup নেয়, এবং rollback করার উপায় থাকে

এই নীতিগুলো ইচ্ছাকৃতভাবে রাখা হয়েছে যাতে AURA কখনো নিজে থেকে এমন কিছু করে না বসে
যেটা তুমি চাওনি বা যেটা ফিরিয়ে আনা যায় না। ভবিষ্যতে upgrade করার সময় এই
guardrail গুলো অক্ষত রাখাই ভালো।

পুনরায় Dev Environment সেটআপ করার কমান্ড:
:: ১. Repo ফিরিয়ে আনুন
cd D:\
git clone https://github.com/faysalahmedbhuiyan/AURA.git
cd AURA

:: ২. Backend — Python virtual environment (dev-এর জন্য, python-portable না — ওটা শুধু প্যাকেজিং-এর জন্য)
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

:: ৩. Environment file বসান
copy .env.example .env
:: .env খুলে দরকার হলে OLLAMA_MODEL, path গুলো ঠিক করে নিন

:: ৪. Frontend — Node dependencies
cd ..\frontend
npm install
এবার এডিট করে সরাসরি রান/টেস্ট করতে

Backend চালাতে (কোড বদলালে নিজে থেকেই reload হবে):
cd D:\AURA\backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
টেস্ট: browser-এ http://127.0.0.1:8000/api/v1/health অথবা http://127.0.0.1:8000/docs

Frontend + Electron একসাথে dev মোডে (প্রতিবার পুরো installer বানানো লাগবে না, দ্রুত loop):
cd D:\AURA\frontend
npm run electron:dev
শুধু frontend (browser-এ, Electron ছাড়া) দেখতে চাইলে:
npm run dev

Models (sd-turbo-onnx, realistic-vision-onnx ইত্যাদি) — এগুলো ব্যাকআপ (https://drive.google.com/drive/folders/14K4oKfLqZAGY4b3L8uAjzEwHKBLLAHDU?usp=sharing) থেকে D:\AURA\models\ ফোল্ডারে বসাতে হবে যদি আবার download/export এড়াতে চান।
