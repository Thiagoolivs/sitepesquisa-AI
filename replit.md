# Pesquisa AI

## Visão Geral

Plataforma de pesquisa para criar formulários, coletar respostas e realizar análise estatística com IA. Construída em Django (Python) com PostgreSQL.

## Stack

- **Framework**: Django 5.2
- **Python**: 3.11+
- **Banco de dados**: PostgreSQL (via variáveis `PG*`)
- **IA**: Groq API (Llama 3.1) — requer `GROQ_API_KEY` nos Secrets
- **Sessões**: Django sessions no banco de dados (`django.contrib.sessions.backends.db`)
- **Frontend**: Vanilla JS + Chart.js 4 (sem Node.js/React)

## Estrutura

```text
pesquisa_ai/                  # Raiz do projeto Django
├── manage.py                 # Ponto de entrada para comandos Django
├── requirements.txt          # Dependências Python
├── config/                   # Configuração do projeto Django
│   ├── settings.py           # Configurações (DB, sessões, estáticos)
│   ├── urls.py               # Roteamento raiz de URLs
│   └── wsgi.py               # Entrypoint WSGI (para produção)
├── core/                     # App principal
│   ├── views.py              # Views + lógica de estado por sessão
│   ├── urls.py               # Padrões de URL
│   ├── models.py             # Modelo SavedAnalysis
│   ├── services.py           # Parsing de CSV, estatísticas e chamada Groq
│   ├── migrations/           # Migrações do banco de dados
│   └── templatetags/
│       └── json_filters.py   # Filtro |tojson para templates
├── templates/                # Templates HTML
│   ├── base.html             # Layout, navbar, Chart.js, sistema de toast
│   ├── dashboard.html        # Cards de estatísticas + gráficos
│   ├── pesquisa.html         # Abas de formulário/respostas/resultados
│   └── ia.html               # Análise IA via Groq
└── static/
    └── css/
        └── style.css         # Estilos globais
```

## Executando em Desenvolvimento

```bash
cd pesquisa_ai && python manage.py runserver 0.0.0.0:5000
```

## Funcionalidades Principais

- **Dashboard**: Análise de CSV com detecção automática de colunas numéricas e categóricas
- **Formulário de pesquisa**: Tipos de pergunta numérica, múltipla escolha e texto livre
- **Resultados**: Estatísticas por pergunta com gráficos Chart.js
- **Análise IA**: Insights em português via Groq; graceful fallback se a chave ausente
- **Estado de sessão**: Análise ativa armazenada em `request.session['active_analysis']`; pode ser salva no DB (`SavedAnalysis`)

## Variáveis de Ambiente

| Variável | Descrição |
|---|---|
| `SESSION_SECRET` | Chave secreta do Django |
| `GROQ_API_KEY` | Chave de API do Groq (features de IA) |
| `PGDATABASE` | Nome do banco PostgreSQL |
| `PGUSER` | Usuário do banco |
| `PGPASSWORD` | Senha do banco |
| `PGHOST` | Host do banco |
| `PGPORT` | Porta do banco (padrão: 5432) |

## Regras de Parsing de CSV

- Colunas com fragmentos de timestamp (`_at`, `timestamp`, `date`, etc.) → descartadas silenciosamente
- Colunas de consentimento (`consent`, `concordo`, etc.) → tipo `consent` com mensagem fixa
- ≥ 80% dos valores parseáveis como float → coluna numérica
- Demais colunas → categóricas (frequências em `labels`/`values`)
