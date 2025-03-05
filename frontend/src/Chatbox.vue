<template>
  <div class="chatbox">
    <div class="messages" ref="messagesContainer">
      <div v-for="(msg, index) in messages" :key="index" :class="['message', msg.type]">
        {{ msg.text }}
      </div>
    </div>
    <div class="input-area">
      <input v-model="input" @keydown.enter="sendMessage" :disabled="loading" placeholder="Type a message" />
      <button @click="sendMessage" :disabled="loading">
        {{ loading ? "Masterminding an answer..." : "Send" }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, useTemplateRef, onUpdated, onMounted } from "vue";
import axios from "axios";

const messages = ref([
  { text: "Greetings. How may I be of assistance?", type: "bot" }, // TODO get initial message from LLM.
]);
const token = ref(null);
const input = ref("");
const loading = ref(false);
const messagesContainer = useTemplateRef('messagesContainer');

const startSession = async () => {
  const res = await axios.get("http://localhost:5000/start_session", {
    headers: token.value ? { Authorization: token.value } : {}
  });
  token.value = res.data.token;
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
  
  messages.value.push({ text: input.value, type: "user" });
  loading.value = true;
  
  try {
    const res = await axios.post(
      "http://localhost:5000/chat",
      { message: input.value },
      { headers: { Authorization: token.value, ContentType: "application/json" } }
    );
    messages.value.push({ text: res.data.response, type: "bot" });
    // messages.value.push({ text: "\n\n\n\n n\n\n\n n\n\n\n n\n\n\n n\n\n\n n\n\n\n n\n\n\n n\n\n\n n\n\n\n ", type: "bot" });
  } catch (error) {
    if (error.response?.status === 401) {
      alert("Session expired. Renewing token...");
      await startSession();
      await sendMessage();
      location.reload();
    }
    console.error("Error calling LLM: ", error);
    messages.value.push({ text: "Error: Could not connect to the LLM.", type: "bot" });
  } finally {
    input.value = "";
    loading.value = false;
    scrollToBottom();
  }
}

</script>
