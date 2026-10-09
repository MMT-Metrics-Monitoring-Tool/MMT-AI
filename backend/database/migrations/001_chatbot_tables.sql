-- Chatbot tables in the MMT database. Prefixed with chatbot_ to keep them apart from MMT's own tables.
-- Applied automatically on backend startup (DB_AUTO_MIGRATE=true). Safe to run repeatedly.

CREATE TABLE IF NOT EXISTS chatbot_conversations (
  id CHAR(36) NOT NULL PRIMARY KEY,
  user_id VARCHAR(64) NOT NULL,
  project_id INT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_chatbot_conversations_user (user_id, project_id)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS chatbot_messages (
  id CHAR(36) NOT NULL PRIMARY KEY,
  conversation_id CHAR(36) NOT NULL,
  role VARCHAR(16) NOT NULL,
  content MEDIUMTEXT NOT NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  model VARCHAR(128) NULL,
  prompt_version VARCHAR(16) NULL,
  first_token_ms INT NULL,
  total_ms INT NULL,
  prompt_tokens INT NULL,
  completion_tokens INT NULL,
  error TEXT NULL,
  INDEX idx_chatbot_messages_conversation (conversation_id, created_at),
  CONSTRAINT fk_chatbot_messages_conversation FOREIGN KEY (conversation_id)
    REFERENCES chatbot_conversations (id) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS chatbot_feedback (
  message_id CHAR(36) NOT NULL PRIMARY KEY,
  user_id VARCHAR(64) NOT NULL,
  rating TINYINT NOT NULL,
  comment TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_chatbot_feedback_message FOREIGN KEY (message_id)
    REFERENCES chatbot_messages (id) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
