# Skyper

Skyper is a personal Agent workspace rebuilt from the Argus RAG platform. It keeps the existing FastAPI, PostgreSQL/pgvector, Elasticsearch, MinIO and LangGraph backend while adding a new workspace UI and an offline Agent regression layer.

## What is new

- A dark, focused Skyper workspace with overview, Agent, knowledge-base and document navigation.
- A local theme panel: upload an image, choose an accent, and adjust the background mask. The image stays in browser `localStorage`; it is never sent to the backend.
- `Argus-python/app/evaluation/`: dependency-free trace evaluation for tool choice, required arguments, role denial and human confirmation.
- `Argus-python/tests/test_agent_regression.py`: deterministic pytest regression cases that do not call an LLM.

## Run the offline evaluator

```powershell
cd Argus-python
python -m app.evaluation.runner
pytest -q tests/test_agent_regression.py
```

## Run the application

1. Copy `Argus-python/.env.example` to `Argus-python/.env`, replace the model keys and set a unique `AUTH_JWT_SECRET`.
2. Start PostgreSQL, MinIO and Elasticsearch with `docker compose up -d` from this directory.
3. Install backend dependencies and run `uvicorn app.main:app --host 127.0.0.1 --port 10001 --reload`.
4. In another terminal, run `npm install` and `npm run dev` inside `Argus-frontend`.

The web app is at `http://localhost:5173`. The development admin is controlled by `DEV_ADMIN_ENABLED`, `DEV_ADMIN_USERNAME` and `DEV_ADMIN_PASSWORD` in `.env`.
