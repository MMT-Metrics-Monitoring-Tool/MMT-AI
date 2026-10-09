import os

# Required by the app factory. Set before any app module is imported, so no real .env values are used.
os.environ.update({
    "MODEL_NAME": "test-model",
    "API_BASE_URL": "http://llm.invalid/v1",
    "API_KEY": "test-key",
    "JWT_SECRET_KEY": "test-secret-key-that-is-at-least-32-bytes",
    "JWT_ALGORITHM": "HS256",
    "AUTH_DEV_MODE": "false",
})
