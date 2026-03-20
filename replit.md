# Pesquisa AI

## Overview

A survey platform for creating forms, collecting responses, and performing AI-driven statistical analysis. Built entirely with Django (Python).

## Stack

- **Framework**: Django 5.2
- **Python**: 3.11+
- **AI**: Groq API (Llama 3.1) — requires `GROQ_API_KEY` env variable
- **Server**: Gunicorn
- **Sessions**: File-based Django sessions (`/tmp/pesquisa_sessions`)
- **Frontend**: Vanilla JS + Chart.js 4 (no Node.js/React)

## Structure

```text
artifacts/pesquisa-flask/     # Main Django application
├── config/                   # Django project config
│   ├── settings.py           # Settings (sessions, middleware, static)
│   ├── urls.py               # Root URL routing
│   └── wsgi.py               # WSGI entrypoint for gunicorn
├── core/                     # Main app
│   ├── views.py              # All views + API endpoints (session-based state)
│   ├── urls.py               # URL patterns
│   └── stats.py              # Statistical calculations (mean, median, mode, etc.)
├── templates/                # Django HTML templates
│   ├── base.html             # Layout, navbar, Chart.js, toast system
│   ├── dashboard.html        # Stats cards + bar/line charts
│   ├── pesquisa.html         # Survey builder/responder/results tabs
│   └── ia.html               # AI analysis via Groq
└── static/css/style.css      # All styles
```

## Key Features

- **Dashboard**: Manual number input, CSV upload, interactive Chart.js bar + line charts
- **Survey builder**: Numeric, multiple choice, and free-text question types
- **Survey results**: Per-question stats with charts (numeric) and pie/bar charts (multiple choice)
- **AI Analysis**: Groq-powered insights in Portuguese; fallback logic when API key missing
- **Session state**: Form, responses and analysis stored in Django file sessions (no DB needed)

## Running

```bash
cd artifacts/pesquisa-flask && gunicorn --bind 0.0.0.0:5000 --reuse-port --reload config.wsgi:application
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET/POST | `/formulario` | Get or save survey form |
| POST | `/formulario/responder` | Submit answers |
| GET | `/formulario/dados?pergunta_id=` | Per-question data |
| GET | `/formulario/analise` | Bulk analysis of all questions |
| POST | `/analisar` | Analyze a list of numbers |
| POST | `/upload_csv` | Upload and analyze CSV |
| POST | `/ia_api` | Groq AI question |
| POST | `/ia_csv` | CSV upload + AI auto-analysis |

## Environment Variables

- `SESSION_SECRET` — Django secret key
- `GROQ_API_KEY` — Groq API key for AI features (optional; fallback logic included)
