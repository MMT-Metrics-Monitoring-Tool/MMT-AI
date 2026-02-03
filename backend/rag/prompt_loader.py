import os
import time


class PromptLoader:
    """A class for handling dynamic loading of prompts from text files.
    This allows for in-place prompt updates without restarting the system.
    TODO Switch TTL with a watchdog or read prompts from a database.
    """
    def __init__(self, prompt_dir="./prompts", cache_ttl_seconds=30):
        self.prompt_dir = prompt_dir
        self.cache_ttl_seconds = cache_ttl_seconds
        self._last_loaded = 0
        self._cache = {}

    def _load_file(self, filename):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), self.prompt_dir, filename)
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def get_prompt(self, name):
        now = time.time()
        if (now - self._last_loaded) > self.cache_ttl_seconds:
            self._cache = {}
            self._last_loaded = now
        if name not in self._cache:
            self._cache[name] = self._load_file(f"{name}.txt")
        return self._cache[name]

