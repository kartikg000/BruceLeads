# 🥊 BruceLeads

**Agentic Lead Generation & Outreach System**

Scrape high-intent leads from Google Maps & social media, enrich them with contact details, generate hyper-personalized cold emails using Gemini AI, and send via Gmail — all from a modern React dashboard with a first-run setup wizard.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![React](https://img.shields.io/badge/React-19-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔍 **Google Maps Scraper** | Extract business names, phones, websites, addresses |
| 🌐 **Social Media Search** | Find leads on LinkedIn, Twitter, Reddit, Instagram, Facebook via Google X-ray |
| 📧 **Lead Enrichment** | Auto-find owner names & emails from business websites |
| 🤖 **AI Email Generation** | Gemini 1.5 Flash writes personalized emails (AIDA/PAS/Follow-up) |
| ✍️ **Email Studio** | AI-powered customization — adjust tone, length, style per email |
| 📤 **Gmail Integration** | Create drafts or send emails via OAuth / SMTP fallback |
| 📊 **Outbox** | Review, select, and batch-send with per-lead control |
| ⚙️ **Setup Wizard** | First-run wizard — provide your own API keys and credentials |
| 🎛️ **Performance Controls** | Adjustable browser concurrency, scraping delay, AI temperature |
| 📦 **EXE Distribution** | Build a standalone Windows executable |
| 💾 **Export** | Download leads as CSV |

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/yourusername/BruceLeads.git
cd BruceLeads

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### 2. Start the App

```bash
# Terminal 1 — Backend
python run_app.py

# Terminal 2 — Frontend
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** in your browser. The **Setup Wizard** will guide you through configuring your API keys on first launch.

### 3. (Optional) Environment File

You can also configure credentials via `.env`:

```bash
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux
```

> **Note:** The Setup Wizard and Settings page store credentials in `data/settings.json`, which takes priority over `.env`.

---

## 📖 Usage Guide

### Workflow

```
1. SCRAPE → 2. ENRICH → 3. GENERATE → 4. REVIEW → 5. SEND
```

| Step | Page | What Happens |
|------|------|-------------|
| **Scrape** | Find Leads | Search Google Maps or social media for businesses |
| **Enrich** | Manage Leads | Parallel browser tabs find emails from business websites |
| **Generate** | Email Studio | AI writes personalized cold emails using your chosen framework |
| **Review** | Outbox | Expand, edit, and approve each email before sending |
| **Send** | Outbox | Create Gmail drafts or send directly |

### Email Frameworks

| Framework | Best For |
|-----------|----------|
| **AIDA** | General cold outreach, building curiosity |
| **PAS** | Problem-focused services, pain-point selling |
| **Follow-up** | Re-engaging leads who haven't responded |

---

## 📁 Project Structure

```
BruceLeads/
├── run_app.py              # App launcher (dev & EXE mode)
├── config.py               # Hybrid config (settings.json + .env)
├── build.bat               # Windows EXE build script
├── requirements.txt        # Python dependencies
├── .env.example            # Environment template
│
├── backend/                # FastAPI backend
│   ├── main.py             # App, CORS, router setup
│   ├── dependencies.py     # Shared DB instance
│   └── api/
│       ├── leads.py        # Lead CRUD + CSV import/export
│       ├── scraper.py      # Google Maps & social scraping
│       ├── email.py        # AI email generation & sending
│       ├── gmail.py        # Gmail OAuth connect/disconnect
│       ├── sessions.py     # Browser session management
│       └── setup.py        # Setup wizard & runtime settings API
│
├── frontend/               # React 19 + Vite + Tailwind
│   └── src/
│       ├── App.jsx          # Router + setup wizard gate
│       ├── components/
│       │   ├── Layout.jsx   # Sidebar navigation
│       │   ├── SetupWizard.jsx  # First-run configuration wizard
│       │   └── LeadTable.jsx    # Reusable data table
│       └── pages/
│           ├── Dashboard.jsx    # Stats overview
│           ├── FindLeads.jsx    # Scraping interface
│           ├── ManageLeads.jsx  # Lead management & enrichment
│           ├── EmailStudio.jsx  # AI email generation
│           ├── Outbox.jsx       # Email review & sending
│           └── Settings.jsx     # Credentials, performance, Gmail OAuth
│
├── models/
│   ├── lead.py             # Lead dataclass + status enum
│   └── database.py         # JSON-based storage with dedup
│
├── scrapers/
│   ├── google_maps.py      # Google Maps wrapper (subprocess)
│   ├── social_media.py     # Social media wrapper (subprocess)
│   ├── enrichment.py       # Email enrichment wrapper
│   ├── worker.py           # Maps Playwright worker
│   ├── social_worker.py    # Social Playwright worker
│   ├── enrich_worker.py    # Async enrichment worker
│   └── session_manager.py  # Browser profile management
│
├── emailer/
│   ├── composer.py         # Gemini AI email composer
│   ├── templates.py        # AIDA/PAS/Follow-up templates
│   ├── gmail_client.py     # Gmail API + SMTP client
│   └── oauth_setup.py      # Gmail OAuth helper
│
├── utils/
│   ├── validators.py       # Email/URL validation
│   └── rate_limiter.py     # Rate limiting
│
├── data/                   # Runtime data (auto-created)
│   ├── leads.json          # Lead database
│   └── settings.json       # User settings (from wizard/settings page)
│
└── credentials/            # OAuth credentials (auto-created)
```

---

## ⚙️ Configuration

Settings can be changed in the **Settings** page (saved to `data/settings.json`) or via `.env`:

| Setting | Default | Description |
|---------|---------|-------------|
| `GEMINI_API_KEY` | — | Google Gemini API key (**required**) |
| `GMAIL_ADDRESS` | — | Gmail address for SMTP fallback |
| `GMAIL_APP_PASSWORD` | — | Gmail App Password for SMTP |
| `MAX_CONCURRENT_BROWSERS` | 3 | Parallel browser tabs (1-10) |
| `SCRAPING_DELAY` | 2.0 | Seconds between scrape requests |
| `GEMINI_TEMPERATURE` | 0.7 | AI creativity (0.0-2.0) |
| `MAX_EMAIL_WORDS` | 150 | Max words per generated email |

### Gmail OAuth (for Draft Creation)

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project and enable the **Gmail API**
3. Create OAuth 2.0 credentials (Desktop app type)
4. Download the JSON file
5. Upload via Setup Wizard or save to `credentials/gmail_credentials.json`
6. Click **Connect Gmail** in Settings

See [docs/gmail_setup.md](docs/gmail_setup.md) for detailed instructions.

---

## 📦 Building an EXE

Create a standalone Windows executable that anyone can run:

```bash
# Run the build script
build.bat
```

This will:
1. Build the React frontend (`npm run build`)
2. Package everything with PyInstaller
3. Output to `dist/BruceLeads/`

To distribute: zip the `dist/BruceLeads/` folder. Recipients just run `BruceLeads.exe` — it opens the app in their browser and the Setup Wizard handles API key configuration.

> **Note:** Recipients still need to install Playwright browsers separately:  
> `playwright install chromium`

---

## ⚠️ Important Notes

### Rate Limiting
- Google Maps scraping includes random delays to avoid detection
- Gmail API has daily sending limits (500/day for consumer accounts)

### Legal Considerations
- Always comply with CAN-SPAM, GDPR, and local regulations
- Provide opt-out mechanisms in your emails
- Only contact businesses that would benefit from your services

### Best Practices
- Start with small batches (10-20 leads) to test your messaging
- Review all AI-generated emails before sending
- Use drafts first to review in Gmail before sending
- Adjust browser concurrency based on your system's RAM

---

## 🛠️ Development

```bash
# Backend (auto-reloads)
python run_app.py

# Frontend (hot reload)
cd frontend && npm run dev
```

The Vite dev server proxies `/api`, `/stats`, `/config` to `localhost:8000`.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- [React](https://react.dev/) — Frontend framework
- [FastAPI](https://fastapi.tiangolo.com/) — Backend framework
- [Playwright](https://playwright.dev/) — Browser automation
- [Google Gemini](https://ai.google.dev/) — AI email generation
- [Tailwind CSS](https://tailwindcss.com/) — Styling
- [Framer Motion](https://www.framer.com/motion/) — Animations

---

Made with 💪 by Kartik Gupta
