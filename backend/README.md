# How it works

Each question is answered with a single LLM call. Everything the model needs is assembled in code first (`chatbot/context.py`):

1. **Course material**: the course pages (`chatbot/course_content.py`), converted to Markdown and re-fetched every `COURSE_CONTENT_TTL` seconds. They are small enough (~5k tokens) to be included in full, so no retrieval is needed.
2. **Upcoming dates**: dated items extracted from the course pages and sorted relative to today (`chatbot/deadlines.py`), so the model does not have to calculate dates.
3. **Project data**: the team's live MMT data, fetched for every question (`database/sql_executor.py`, `get_project_snapshot`), with computed summary figures such as hours vs. target.
4. **Conversation history** from the database, then the question.

The system prompt is `chatbot/prompts/system.txt`. It is reloaded without a restart, and a hash of it is stored with every answer as the prompt version.

Questions, answers, timings, token usage, errors and feedback are stored in the `chatbot_` tables of the MMT database (`database/migrations/`). The tables are created on startup when `DB_AUTO_MIGRATE=true`.

The LLM is accessed through any OpenAI-compatible API (`chatbot/llm.py`), so changing the model or provider only requires changing `MODEL_NAME`, `API_BASE_URL` and `API_KEY`.

## API

- `POST /chat` with `{"prompt", "project_id", "conversation_id"?}` streams server-sent events: `start` (`conversation_id`), `status` (progress text), `token` (answer text, repeated), then `done` (`message_id`) or `error`.
- `POST /feedback` with `{"message_id", "rating": 1 | -1, "comment"?}`.
- `GET /health` checks the database and the LLM API.
- `GET /start_session` issues a development token. Only available when `AUTH_DEV_MODE=true`.

## Authentication (token contract with MMT)

MMT issues the chatbot token and passes it to the widget in its `data-token` attribute. When the backend answers 401, the widget gets a new token from MMT's `data-refresh-url` and retries (see [frontend/README.md](../frontend/README.md)). Requests carry the token as-is in the `Authorization` header.
The token is a JWT signed with the shared `JWT_SECRET_KEY` using `JWT_ALGORITHM`, with these claims:

| Claim | Type | Description |
| --- | --- | --- |
| `sub` | string | MMT user ID |
| `project_ids` | list of integers | Projects the user may access, e.g. their own project, or all supervised projects for a coach |
| `name` | string, optional | Display name |
| `exp` | number | Expiry time. Keep it short, e.g. 30 minutes |

The backend rejects requests for projects not listed in `project_ids` (HTTP 403), and conversations and feedback are tied to `sub`.

Example of issuing a token in PHP with `firebase/php-jwt`:

```php
$token = \Firebase\JWT\JWT::encode([
    'sub' => (string)$user->id,
    'project_ids' => $projectIdsTheUserCanView,
    'name' => $user->first_name,
    'exp' => time() + 1800,
], $sharedSecret, 'HS256');
```

For local development without MMT, set `AUTH_DEV_MODE=true`. `/start_session` then issues tokens for the projects in `DEV_PROJECT_IDS`. When dev mode is off, it answers 404. Never enable it in production.

In MMT the secret is `AiChat.jwtSecret` (`AI_CHAT_JWT_SECRET`) and the token lifetime `AiChat.tokenTtl` (`AI_CHAT_TOKEN_TTL`, seconds). To test token renewal locally, set the lifetime to e.g. 10 seconds.

# Installation

## Dependencies

Requires Python 3.13.

Create a virtual environment and ensure that `pip` version 25.3 is installed. Version 26 causes in-library errors (as of 2026-02-04).

Install dependencies from the `requirements.txt` file. For running tests, install `requirements-dev.txt`.

## Application

Copy `dotenv` (in the repository root) to `.env` next to it. Both the Makefile (`../.env`) and `python main.py` read it from there. Set the following required values:

- `MODEL_NAME` — the model identifier to use (e.g. `Qwen3.8-27B-AIC`)
- `API_BASE_URL` — the API endpoint URL (e.g. `https://aviary.fgl.rd.tuni.fi/api/` NOTE! Use TUNI VPN!)
- `API_KEY` — your API key
- `JWT_SECRET_KEY` — a pseudorandom secret string, min. 32 bytes recommended. Must be the same secret MMT uses to sign chatbot tokens.
- `AUTH_DEV_MODE` — `true` only for local development without MMT (see Authentication).
- `DB_HOST` — the database hostname. For Docker, use the database container service name `mariadb`.
- `DB_PORT` — the database port, usually `3306` for MariaDB/MySQL.
- `DB_USER`, `DB_PASS`, `DB_NAME` — database credentials/schema.
- `CORS_ORIGINS` — comma-separated origins allowed to call the API. Use the MMT address on servers (locally e.g. `http://localhost`); the default `*` allows any.

Optional settings, with their values in `dotenv`:

| Setting | Value | Description |
| --- | --- | --- |
| `LLM_TEMPERATURE`, `LLM_MAX_TOKENS` | `0.3`, `4000` | LLM sampling and answer length (includes hidden reasoning tokens) |
| `LLM_EXTRA_BODY` | `{"chat_template_kwargs": {"enable_thinking": false}}` | Provider-specific options as JSON. Turns Qwen's hidden thinking off, which cuts the time to the first token from ~7–60 s to ~1.5 s with equal eval results. Leave empty for models that do not support it |
| `JWT_ALGORITHM` | `HS256` | Must match the algorithm MMT signs with |
| `DEV_PROJECT_IDS` | `1` | Projects a development token can access |
| `HISTORY_MESSAGES` | `10` | Earlier messages sent with each question |
| `MAX_PROMPT_CHARS` | `2000` | Longer questions are rejected with 413 |
| `RATE_LIMIT_REQUESTS`, `RATE_LIMIT_WINDOW_SECONDS` | `20`, `600` | Questions per user per window, then 429 |
| `COURSE_CONTENT_TTL` | `21600` | Seconds between re-fetches of the course pages |
| `DB_POOL_SIZE` | `5` | Database connection pool size |
| `DB_AUTO_MIGRATE` | `true` | Create the `chatbot_` tables on startup if missing |

After changing `.env`, recreate the container with `make run`; `make start` keeps the old values.

## Before running
### EduVPN 
Install [EduVPN](https://www.eduvpn.org/client-apps/)

Run as Tampere Universities


### MMT database configuration
For the Docker setup, keep the backend and MariaDB containers on the shared
Docker network `mmt-shared`. The backend should use `mariadb` as `DB_HOST`,
which allows container-to-container access without exposing MariaDB through the
host.

## Development
Run for development using 
```sh 
python main.py
```

## Docker

The Docker image creates a virtual environment and installs `pip==25.3` before
installing `requirements.txt`.

The backend Docker setup assumes the database is reachable from the backend
container over the shared Docker network `mmt-shared`. 

Run the backend BEFORE running MMT to make sure the network is created. 

If the network is not created by backend create it: 
```sh
docker network create mmt-shared
```

Other containers on `mmt-shared` can reach the backend at
`http://mmt-backend:8000`. MMT uses this address for its health check. Browsers
cannot use it: the widget calls the backend at the published port
(`http://localhost:8000` locally), or on servers at a public HTTPS address in
front of the backend.

The Makefile reads environment values from `../.env` by default. 

Build and run from the backend directory:

```sh
make run
```

Stop the container without deleting the image:

```sh
make stop
```

Start the existing stopped container without rebuilding:

```sh
make start
```

Remove the backend container and image:

```sh
make clean
```

## Tests and evaluations

Unit tests need no database, LLM or network access:

```sh
make test                       # or: python -m pytest
```

The evaluation questions in `evals/cases.json` are run against the configured LLM with a fixed date and fixture project data (`evals/fixtures/`), and each answer is checked with regular expressions. Run them after every prompt or model change, and add a case for every wrong answer found in use:

```sh
make eval                       # or: python -m evals.run
make eval ARGS="--repeat 3"     # each question three times, to see how stable the answers are
```

Results are also saved as JSON in `evals/results/`.

---

curl copy-paste for convenience (requires `AUTH_DEV_MODE=true`):

```sh
TOKEN=$(curl -s localhost:8000/start_session | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")
curl -N localhost:8000/chat -H "Content-Type: application/json" -H "Authorization: $TOKEN" -d '{"prompt": "What is due next?", "project_id": 1}'
```
