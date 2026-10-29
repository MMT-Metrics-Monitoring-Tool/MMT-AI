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
// Backend address and MMT's token renewal URL, given by MMT through data attributes (see main.js).
const apiUrl = inject("apiUrl", import.meta.env.VITE_API_URL ?? "http://localhost:8000");
const refreshUrl = inject("refreshUrl", null);
// Sent with each question so the backend can include earlier messages. Set by the backend's first "start" event.
const conversationId = ref(null);
const messagesContainer = useTemplateRef('messagesContainer');
// True when the widget runs on its own and the backend refused /start_session because AUTH_DEV_MODE is off.
const devModeOff = ref(false);
const DEV_MODE_OFF_TEXT = "The chatbot is running without MMT, but the backend's AUTH_DEV_MODE is off, so it can't give out a token. Set AUTH_DEV_MODE=true in the backend's .env and restart it.";

// Inside MMT the token comes from MMT. When the widget runs on its own, it gets one from the backend's dev endpoint.
const startSession = async () => {
  if (!token.value && !refreshUrl) {
    try {
      await refreshToken();
    } catch (error) {
      console.error("Error starting session: ", error);
      const text = devModeOff.value ? DEV_MODE_OFF_TEXT : "Error: Could not start a chat session.";
      messages.value.push({ text, rawText: text, type: "bot", error: true });
    }
  }
}

// Gets a new token. Inside MMT it asks MMT, which checks the user's login cookie, so a logged-out user gets a 403 or a redirect to the login page.
// On its own it asks the backend's /start_session, which only works with AUTH_DEV_MODE enabled.
const refreshToken = async () => {
  const res = await fetch(refreshUrl ?? `${apiUrl}/start_session`, { credentials: "same-origin" });
  devModeOff.value = !refreshUrl && res.status === 404;
  const isJson = (res.headers?.get("Content-Type") ?? "").includes("application/json");
  if (!res.ok || !isJson) throw new Error(`Token refresh failed with status ${res.status}`);
  const data = await res.json();
  if (!data.token) throw new Error("Token refresh returned no token");
  token.value = data.token;
}

// POSTs to the backend. On 401 the token is renewed and the request sent once more.
const authorizedFetch = async (path, body = null) => {
  const send = () => fetch(`${apiUrl}${path}`, {
    method: body === null ? "GET" : "POST",
    headers: {
      "Authorization": token.value,
      ...(body !== null && { "Content-Type": "application/json" }),
    },
    ...(body !== null && { body: JSON.stringify(body) }),
  });

  const res = await send();
  if (res.status !== 401) return res;
  try {
    await refreshToken();
  } catch (error) {
    console.error("Error refreshing token: ", error);
    return res;
  }
  return send();
}

const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
  }
}

// Restores the latest conversation after a page refresh. If there is none, the greeting stays.
const loadHistory = async () => {
  if (!token.value) return;
  loading.value = true; // blocks sending until the history is in place
  try {
    const res = await authorizedFetch(`/history?project_id=${encodeURIComponent(projectId)}`);
    if (!res.ok) return;
    const data = await res.json();
    if (!data.conversationId || !data.messages?.length) return;

    conversationId.value = data.conversationId;
    messages.value = data.messages.map((m) =>
      m.role === "user"
        ? { text: "", rawText: m.content, type: "user" }
        : {
            text: sanitizeMarkdown(m.content),
            rawText: m.content,
            type: "bot",
            status: "",
            messageId: m.id,
            rating: m.rating ?? 0,
            error: false,
          }
    );
  } catch (error) {
    console.error("Error loading history: ", error);
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  await startSession();
  await loadHistory();
});

onUpdated(scrollToBottom);

const sendMessage = async (questionText = null) => {
  const textToSend = questionText ?? input.value;

  if (!textToSend.trim() || !token.value || loading.value) return;
  
  messages.value.push({ text: "", rawText: textToSend, type: "user" });
  loading.value = true;
  
  try {
    const res = await authorizedFetch("/chat", { prompt: textToSend, project_id: projectId, conversation_id: conversationId.value });

    if (res.ok === false) {
      const errorTexts = {
        401: "Your session has ended. Please reload the page.",
        403: "You don't have access to the chatbot for this project.",
        413: "Your message is too long. Please shorten it and try again.",
        429: "You've asked a lot of questions in a short time. Please wait a minute and try again.",
      };
      const text = res.status === 401 && devModeOff.value
        ? DEV_MODE_OFF_TEXT
        : errorTexts[res.status] ?? "Error: Could not connect to the LLM.";
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
    await authorizedFetch("/feedback", { message_id: msg.messageId, rating });
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
