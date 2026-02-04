from functools import partial
from cachetools import TTLCache
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import SystemMessage
from langchain_core.runnables.history import RunnableWithMessageHistory
from typing import Tuple

import os
import uuid
import datetime
import jwt


class SessionManager:
    """A class for handling all user session data.
    This includes all user-specific overhead, such as runnables.
    """
    def __init__(self, chain, system_prompt, database_prompt, get_project_data, secret_key, algorithm):
        self.chain = chain
        self.system_prompt = system_prompt
        self.database_prompt = database_prompt
        self.get_project_data = get_project_data
        self.secret_key = secret_key
        self.algorithm = algorithm

        MAX_SESSIONS = int(os.getenv("MAX_SESSIONS", 50))
        SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", 1800))
        self.session_ttl_seconds = SESSION_TTL_SECONDS

        self.sessions = TTLCache(maxsize=MAX_SESSIONS, ttl=SESSION_TTL_SECONDS)
        self.histories = TTLCache(maxsize=MAX_SESSIONS, ttl=SESSION_TTL_SECONDS)
        self.runnables = TTLCache(maxsize=MAX_SESSIONS, ttl=SESSION_TTL_SECONDS)

    def generate_jwt_token(self, existing_session_id: str | None = None) -> str:
        """Generates a JWT token. Tokens are used for identifying front-end sessions.

        Args:
            existing_session_id (str, optional): The existing session ID signifying the renewal of an existing token. Defaults to None.

        Returns:
            str: The generated JWT token.
        """
        session_id = existing_session_id if existing_session_id else str(uuid.uuid4())
        expiration = datetime.datetime.utcnow() + datetime.timedelta(seconds=self.session_ttl_seconds)

        # Set initial timestamp. It is not technically required as TTLCache already handles timeouts, but it is useful for debugging.
        self.sessions[session_id] = datetime.datetime.utcnow()

        payload = {"session_id": session_id, "exp": expiration}
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def validate_jwt_token(self, token: str) -> str:
        decoded = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        session_id = decoded["session_id"]

        self.sessions[session_id] = datetime.datetime.utcnow() # Refresh timestamp.
        return session_id
    
    def _get_system_prompt_with_data(self, data: str) -> str:
        """Appends the system and database prompts.

        Args:
            data (str): The data to inject into the database prompt.

        Returns:
            str: The combined prompt including data.
        """
        return self.system_prompt + "\n\n" + self.database_prompt.format(data=data)
    
    def get_history(self, session_id: str, project_id: int | None = None):
        """Get session history for the given session ID.

        Fetches the sessions message history. Delegates history creation to create_session_history() it if it does not exist yet.
        Project ID is specifically needed for the creation of new session history.

        Args:
            session_id (str): ID of the session to get history for.
            project_id (int): ID of the project to fetch data for if creating a new history.

        Returns:
            BaseChatMessageHistory: The retrieved message history of the session.
        """
        # TODO Key by (session_id, project_id) when relevant.
        if session_id not in self.histories:
            history = InMemoryChatMessageHistory()
            if not project_id:
                history.add_message(SystemMessage(self.system_prompt))
            else:
                data = self.get_project_data(project_id)
                combined_prompt = self._get_system_prompt_with_data(data)
                history.add_message(SystemMessage(combined_prompt))
            self.histories[session_id] = history
        return self.histories[session_id]

    def get_runnable(self, session_id: str, project_id: int) -> RunnableWithMessageHistory:
        key: Tuple[str, int] = (session_id, project_id)
        runnable = self.runnables.get(key)
        if runnable is None:
            runnable = RunnableWithMessageHistory(
                    self.chain,
                    partial(self.get_history, project_id=project_id),
                    input_messages_key="question",
                    history_messages_key="messages",
            )
            self.runnables[key] = runnable
        return runnable

    def get_active_session_count(self):
        return len(self.sessions)

