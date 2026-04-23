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
- `JWT_SECRET_KEY` — a pseudorandom secret string, min. 32 bytes recommended
- `DB_HOST` — the database hostname. For Docker, use the database container service name `mariandb`.
- `DB_PORT` — the database port, usually `3306` for MariaDB/MySQL.
- `DB_USER`, `DB_PASS`, `DB_NAME` — database credentials/schema.

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
`http://mmt-backend:8000`.

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

Remove the backend container, image, and Chroma volume:

```sh
make clean
```

---

curl copy-paste for convenience:

```curl localhost:8000/start_session```

Copy received token into Authorization and execute:

```curl localhost:8000/chat -H "Content-Type: application/json" -H "Authorization: " -d '{"prompt": "Summarize requirements collection in software engineering"}'```
