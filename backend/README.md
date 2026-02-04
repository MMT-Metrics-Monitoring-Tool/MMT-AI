# Installation

## Dependencies

Requires Python 3.13. Ollama is required for local execution.

Create a virtual environment and ensure that `pip` version 25.3 is installed. Version 26 causes in-library errors (as of 2026-02-04).

Install dependencies from the `requirements.txt` file.

**Note:**\
On CentOS 9, sqlite3 >= 3.35.0 was required to be manually built for Chroma. Fedora 41+ was fine OOTB.

## Application

Copy the contents of ```dotenv``` to ```.env```. Adjust as needed.

Run for development using ```python main.py```.

Default context window in Ollama models is 2048 tokens. This is hardly enough for any kind of RAG, let alone using project data. 64k was used for the initial prototype implementation.\\
You can build a model with a larger context window by (mistral-nemo used as example, on a Linux machine):
1. Pull the Ollama model ```ollama pull mistral-nemo```.
2. Execute ```ollama show --modelfile mistral-nemo > Modelfile-mistral-nemo-64k```.
3. Edit the created Modelfile.
4. The comment at the top explains what to do with the ```FROM ...``` line depending on the model.
5. Add parameter line ```PARAMETER num_ctx 65536```. Adjust to what size you want to use (and have the resources for).
6. Build the model by ```ollama create mistral-nemo-64k --file Modelfile-mistral-nemo-64k```.
7. Replace the ```MODEL_NAME``` value in ```.env```.

---

curl copy-paste for convenience:

```curl localhost:8000/start_session```

Copy received token into Authorization and execute:

```curl localhost:8000/chat -H "Content-Type: application/json" -H "Authorization: " -d '{"prompt": "Summarize requirements collection in software engineering"}'```
