<template>
  <div class="mmt-ai-chat-widget">
    <div class="chatbox">
      <div class="chatbox-messages" ref="messagesContainer">
        <div
          v-for="(msg, index) in messages"
          :key="index"
          :class="['chatbox-message', msg.type, { error: msg.error }]"
        >
          <template v-if="msg.type === 'user'">{{ msg.rawText }}</template>
          <template v-else>
            <span v-if="msg.status && !msg.rawText" class="chatbox-status">{{ msg.status }}</span>
            <div v-html="msg.text"></div>
            <div v-if="msg.messageId && !msg.error" class="chatbox-feedback">
              <button
                type="button"
                :class="{ selected: msg.rating === 1 }"
                aria-label="Helpful answer"
                title="Helpful"
                @click="sendFeedback(index, 1)"
              >👍</button>
              <button
                type="button"
                :class="{ selected: msg.rating === -1 }"
                aria-label="Unhelpful answer"
                title="Not helpful"
                @click="sendFeedback(index, -1)"
              >👎</button>
            </div>
          </template>
        </div>
      </div>

      <div class="quick-questions-panel">
        <div v-if="!selectedCategory" class="quick-questions-row" role="list">
          <button
            v-for="(category, index) in questionCategories"
            :key="index"
            type="button"
            class="question-chip category-chip"
            :disabled="loading"
            @click="selectedCategory = category"
          >
            {{ category }}
          </button>
        </div>

        <div v-else class="quick-questions-row question-mode" role="list">
          <button
            v-for="(question, index) in categorizedQuestions[selectedCategory]"
            :key="index"
            type="button"
            class="question-chip"
            :disabled="loading"
            @click="sendMessage(question)"
          >
            {{ question }}
          </button>

          <button
            type="button"
            class="question-chip back-chip"
            aria-label="Go back to category selection"
            :disabled="loading"
            @click="selectedCategory = ''"
          >
            Go back
          </button>
        </div>
      </div>
      <div class="input-area">
        <input
          v-model="input"
          @keydown.enter="sendMessage()"
          :disabled="loading"
          placeholder="Type a message"
        />
        <button @click="sendMessage()" :disabled="loading">
          Send
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { inject, onMounted, onUpdated, ref, useTemplateRef } from "vue";
import { marked } from "marked";
import DOMPurify from "dompurify";
import categorizedQuestions from "./categorizedQuestions.json";
import { createSseParser } from "./sse.js";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const questionCategories = Object.keys(categorizedQuestions);
const selectedCategory = ref("");

/**
 * messages contain all messages displayed in the UI.
 * @property {String} text contains the md formatted text, which is primarily used.
 * @property {String} rawText has text without formatting, should be used as a backup for when formatting encounters errors etc., although not strictly necessary if text exists.
 * @property {String} type makes an distinction between "bot" and "user" messages. Used as the message elements' class to map css styles.
 * @property {String} status (bot only) progress text shown until the first part of the answer arrives.
 * @property {String} messageId (bot only) ID of the stored answer, used for feedback.
 * @property {Number} rating (bot only) feedback given by the user: 1, -1 or 0 for none.
 * @property {Boolean} error (bot only) true if the answer failed.
 */
const messages = ref([
  { text: "Greetings. How may I be of assistance?", rawText: "", type: "bot" }, // TODO get initial message from LLM.
]);
const token = ref(inject("token"));
const input = ref("");
const loading = ref(false);
const projectId = inject("projectId");
// Sent with each question so the backend can include earlier messages. Set by the backend's first "start" event.
const conversationId = ref(null);
const messagesContainer = useTemplateRef('messagesContainer');

const startSession = async () => {
  if (!token.value) {
    const res = await fetch(`${API_URL}/start_session`, { method: "GET" });
    const data = await res.json();
    token.value = data.token;
  }
}

const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
  }
}

onMounted(startSession);

onUpdated(scrollToBottom);

const sendMessage = async (questionText = null) => {
  const textToSend = questionText ?? input.value;

  if (!textToSend.trim() || !token.value || loading.value) return;
  
  messages.value.push({ text: "", rawText: textToSend, type: "user" });
  loading.value = true;
  
  try {
    const res = await fetch(`${API_URL}/chat`, {
      method: "POST",
      headers: {
        "Authorization": token.value,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ prompt: textToSend, project_id: projectId, conversation_id: conversationId.value }),
    });

    if (res.status === 401) {
      
      window.top.postMessage("AUTH_EXPIRED_SIGNAL", "*");

      await new Promise((resolve) => {
        const handleMessage = (event) => {
          if (event.data && event.data.type === 'NEW_TOKEN') {
            token.value = event.data.token;
            
            window.removeEventListener('message', handleMessage);
            resolve();
          }
        };

        window.addEventListener('message', handleMessage);
      });

      messages.value.push({ 
        text: `Token expired and refreshed. Please send a new message`, 
        rawText: ``, 
        type: "bot" 
      }); 
      return;
    }

    else if (res.ok === false) {
      const errorTexts = {
        403: "You don't have access to the chatbot for this project.",
        413: "Your message is too long. Please shorten it and try again.",
        429: "You've asked a lot of questions in a short time. Please wait a minute and try again.",
      };
      const text = errorTexts[res.status] ?? "Error: Could not connect to the LLM.";
      messages.value.push({ text, rawText: text, type: "bot", error: true });
      return;
    }

    else if (!res.body) return;

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    messages.value.push({ text: "", rawText: "", type: "bot", status: "", messageId: null, rating: 0, error: false });
    const index = messages.value.length - 1;
    const update = (changes) => {
      messages.value[index] = { ...messages.value[index], ...changes };
    };

    // Receiving response as a stream of server-sent events.
    const parse = createSseParser((event, data) => {
      if (event === "start") {
        conversationId.value = data.conversation_id;
      } else if (event === "status") {
        update({ status: data.text });
      } else if (event === "token") {
        const rawText = messages.value[index].rawText + data.text;
        update({ rawText, text: sanitizeMarkdown(rawText) });
      } else if (event === "done") {
        update({ messageId: data.message_id });
      } else if (event === "error") {
        const rawText = [messages.value[index].rawText, data.text].filter(Boolean).join("\n\n");
        update({ rawText, text: sanitizeMarkdown(rawText), error: true });
      }
    });

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      parse(decoder.decode(value, { stream: true }));
    }
  } catch (error) {
    console.error("Error calling LLM: ", error);
    messages.value.push({ text: "Error: Could not connect to the LLM.", type: "bot" });
  } finally {
    input.value = "";
    loading.value = false;
    scrollToBottom();
  }
}

const sendFeedback = async (index, rating) => {
  const msg = messages.value[index];
  if (!msg.messageId || msg.rating === rating) return;
  messages.value[index] = { ...msg, rating };
  try {
    await fetch(`${API_URL}/feedback`, {
      method: "POST",
      headers: {
        "Authorization": token.value,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ message_id: msg.messageId, rating }),
    });
  } catch (error) {
    console.error("Error sending feedback: ", error);
  }
}

const sanitizeMarkdown = (text) => {
  // Answers can contain text entered by students in MMT, so the generated HTML is sanitized before rendering.
  let html = DOMPurify.sanitize(marked.parse(text));
  // // Remove <p> tags
  html = html.replace(/^<p>/, "").replace(/<\/p>$/, "");
  // // Remove <br> tags without touching single newlines.
  html = html.replace(/\n/g, "<br>");
  return html;
}

</script>
