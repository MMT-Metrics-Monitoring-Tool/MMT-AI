# MMT-AI

This is an LLM module for Metrics Monitoring Tool (MMT).\
For the main MMT project, see https://github.com/MMT-Metrics-Monitoring-Tool/MMT.

## Description

This project contains a chatbot that answers questions about the user's software project and the COMP.SE.610 course.\
Each question is answered with a single LLM call: the backend puts the full course pages, the upcoming course dates (extracted in code) and the user's current MMT project data into the prompt.

The project has two parts:

| Part | Directory | Description |
| --- | --- | --- |
| Backend | [backend/](backend/README.md) | Python (FastAPI) service that answers the questions. Reads project data from the MMT database and stores conversations and feedback in it. Architecture, API, token contract with MMT, tests and evals are described in its README. |
| Chat widget | [frontend/](frontend/README.md) | Vue widget that MMT shows on the project dashboard. Built separately and copied into MMT's `webroot/js/mmt-ai-vue-widget/`. |



## Quick start

1. Copy `dotenv` to `.env` in the repository root and fill in at least `MODEL_NAME`, `API_BASE_URL`, `API_KEY`, `JWT_SECRET_KEY` and the database settings. For Aviary, connect to the TUNI VPN.
2. Start the backend: `cd backend && make run`. This also creates the `mmt-shared` Docker network that MMT uses.
3. Either open MMT, which shows the widget on the project dashboard, or run the widget on its own: set `AUTH_DEV_MODE=true` in `.env`, restart the backend, and run `cd frontend && npm install && npm run dev`.


## Branches

Development for autumn 2026 happens on `autumn26-main`. Create feature branches from it  and open pull requests against it.

## Autumn 26 changes

- **New implementation:** the RAG pipeline (LangChain, ChromaDB, embeddings) is replaced with one LLM call that includes:
  - the full course pages
  - course dates computed in code
  - the live MMT project data

  Also new: tokens signed by MMT (JWT with `project_ids`), conversations and feedback stored in the MMT database (`chatbot_` tables), streamed answers with progress text, feedback buttons, rate limiting, unit tests and evals (`make test`, `make eval`). The Docker image is roughly half the size.