-- Adds chatbot_messages.seq, a monotonically increasing insertion order.
-- Messages are ordered by seq in the widget history and the LLM context, created_at can collide within 
-- the same millisecond and the UUID id is not ordered.
-- IF NOT EXISTS keeps it safe to run repeatedly.

ALTER TABLE chatbot_messages
  ADD COLUMN IF NOT EXISTS seq BIGINT NOT NULL AUTO_INCREMENT UNIQUE;