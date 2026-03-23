# Installation

## Dependencies

Requires Python 3.13.

Create a virtual environment and ensure that `pip` version 25.3 is installed. Version 26 causes in-library errors (as of 2026-02-04).

Install dependencies from the `requirements.txt` file.

**Note:**\
On CentOS 9, sqlite3 >= 3.35.0 was required to be manually built for Chroma. Fedora 41+ was fine OOTB.

## Application

Copy the contents of `dotenv` to `.env`. Set the following required values:

- `MODEL_NAME` — the model identifier to use (e.g. `gemma3-12b`)
- `API_BASE_URL` — the API endpoint URL (e.g. `https://aviary.fgl.rd.tuni.fi/api/` NOTE! Use TUNI VPN!)
- `API_KEY` — your API key
- `EMBEDDING_MODEL_NAME` — the embedding model identifier (e.g.`embeddinggemma-300m`)
- `JWT_SECRET_KEY` — a pseudorandom secret string, min. 32 bytes recommended

Run for development using `python main.py`.

---

curl copy-paste for convenience:

```curl localhost:8000/start_session```

Copy received token into Authorization and execute:

```curl localhost:8000/chat -H "Content-Type: application/json" -H "Authorization: " -d '{"prompt": "Summarize requirements collection in software engineering"}'```
