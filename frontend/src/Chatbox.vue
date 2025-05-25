<template>
  <div class="chatbox">
    <div class="messages" ref="messagesContainer">
      <div v-for="(msg, index) in messages" :key="index" :class="['message', msg.type]" v-html="msg.text"></div>
    </div>
    <div class="input-area">
      <input v-model="input" @keydown.enter="sendMessage" :disabled="loading" placeholder="Type a message" />
      <button @click="sendMessage" :disabled="loading">
        {{ "Send" }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { inject, onMounted, onUpdated, ref, useTemplateRef } from "vue";
import { marked } from "marked";

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
  const res = await fetch("http://localhost:5000/start_session", {
    method: "GET",
    headers: token.value ? { Authorization: token.value } : {}
  });
  const data = await res.json();
  token.value = data.token;
}

const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
  }
}

onMounted(startSession);

onUpdated(scrollToBottom);

const sendMessage = async () => {
  if (!input.value.trim() || !token.value) return;
  
  messages.value.push({ text: input.value, rawText: input.value, type: "user" });
  loading.value = true;
  
  try {
    const res = await fetch( "http://localhost:5000/chat", {
      method: "POST",
      headers: {
        "Authorization": token.value,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ prompt: input.value, project_id: projectId }),
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
      console.log()
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
      await sendMessage();
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
