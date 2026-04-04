# CyberMatch Web App (React + Vite)

## Run Web App

```bash
cd app
npm install
npm run dev
```

## Backend API (from bot folder)

```bash
cd bot
source .venv/bin/activate
pip install -e .
uvicorn app.web.main:app --reload --host 0.0.0.0 --port 8000
```

By default, frontend requests `http://localhost:8000/v1`.

You can override with:

```bash
VITE_API_BASE_URL=http://localhost:8000/v1 npm run dev
```

## Build Frontend

```bash
npm run build
npm run preview
```
