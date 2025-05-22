Update requirements.txt using pipreqs: ```python -m pipreqs.pipreqs . --force```

Ollama required.

Additionally, sqlite3 >= 3.35.0 required for Chroma (Needs manual build for at least CentOS 9).

---

curl copy-paste for convenience:

```curl localhost:5000/start_session```

```curl localhost:5000/chat -H "Content-Type: application/json" -H "Authorization: " -d '{"prompt": "Summarize requirements collection in software engineering"}'```
