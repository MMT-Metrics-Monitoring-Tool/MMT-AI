<template>
  <div class="mmt-ai-chat-widget">
    <div class="chatbox">
      <div class="chatbox-messages" ref="messagesContainer">
        <div
          v-for="(msg, index) in messages"
          :key="index"
          :class="['chatbox-message', msg.type]"
          v-html="msg.text"
        ></div>
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
import categorizedQuestions from "./categorizedQuestions.json";

const questionCategories = Object.keys(categorizedQuestions);
const selectedCategory = ref("");

/**
 * messages contain all messages displayed in the UI.
 * @property {String} text contains the md formatted text, which is primarily used.
 * @property {String} rawText has text without formatting, should be used as a backup for when formatting encounters errors etc., although not strictly necessary if text exists.
 * @property {String} type makes an distinction between "bot" and "user" messages. Used as the message elements' class to map css styles.
 */
const messages = ref([
  { text: "Greetings. How may I be of assistance?", rawText: "", type: "bot" }, // TODO get initial message from LLM.
]);
const token = ref(inject("token"));
const input = ref("");
const loading = ref(false);
const projectId = inject("projectId");
const messagesContainer = useTemplateRef('messagesContainer');

const startSession = async () => {
  const res = await fetch("http://localhost:8000/start_session", {
    method: "GET",
    headers: token.value ? { Authorization: token.value } : {}
  });
  const data = await res.json();
  token.value = data.token;
  localStorage.setItem("chatbot_token", data.token);
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
  
  messages.value.push({ text: textToSend, rawText: textToSend, type: "user" });
  loading.value = true;
  
  try {
    const res = await fetch( "http://localhost:8000/chat", {
      method: "POST",
      headers: {
        "Authorization": token.value,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ prompt: textToSend, project_id: projectId }),
    });
    if (!res.body) return;

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let responseMessage = "";

    messages.value.push({ text: responseMessage, rawText: responseMessage, type: "bot" });

    // Receiving response as a stream.
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      responseMessage += decoder.decode(value, { stream: true });
      
      messages.value[messages.value.length - 1] = {
        text: sanitizeMarkdown(responseMessage),
        rawText: responseMessage,
        type: "bot",
      }
    }
  } catch (error) {
    if (error.response?.status === 401) {
      alert("Session expired. Renewing token...");
      await startSession();
      await sendMessage(textToSend);
    }
    console.error("Error calling LLM: ", error);
    messages.value.push({ text: "Error: Could not connect to the LLM.", type: "bot" });
  } finally {
    input.value = "";
    loading.value = false;
    scrollToBottom();
  }
}

const sanitizeMarkdown = (text) => {
  let html = marked.parse(text);
  // // Remove <p> tags
  html = html.replace(/^<p>/, "").replace(/<\/p>$/, "");
  // // Remove <br> tags without touching single newlines.
  html = html.replace(/\n/g, "<br>");
  return html;
}

</script>
