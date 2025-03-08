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
        {{ "Send" }}
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
    const res = await fetch( "http://localhost:5000/chat", {
      method: "POST",
      headers: {
        "Authorization": token.value,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ prompt: input.value }),
    });
    if (!res.body) return;

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let responseMessage = "";

    messages.value.push({ text: responseMessage, type: "bot" });

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      console.log()
      responseMessage += decoder.decode(value, { stream: true });
      
      messages.value[messages.value.length - 1] = { text: responseMessage, type: "bot" }
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

</script>
