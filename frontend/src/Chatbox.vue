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
import { ref, useTemplateRef, onUpdated, defineExpose } from "vue";

const messages = ref([
  { text: "Greetings. How may I be of assistance?", type: "bot" }, // TODO get initial message from LLM.
]);
const input = ref("");
const loading = ref(false);
const messagesContainer = useTemplateRef('messagesContainer');

onUpdated(() => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
  }
});

const sendMessage = async () => {
  if (input.value.trim()) {
    const userMessage = { text: input.value, type: "user" };
    messages.value.push(userMessage);
    input.value = "";
    loading.value = true;
    
    try {
      // const resp = await fetch("http://localhost:5000/chat", {
      //   method: "POST",
      //   headers: { "Content-Type": "application/json" },
      //   body: JSON.stringify({ prompt: userMessage.text })
      // });
      // const data = await resp.json();
      // messages.value.push({ text: data.response, type: "bot" });
      messages.value.push({ text: "\n\n\n\n n\n\n\n n\n\n\n n\n\n\n n\n\n\n n\n\n\n n\n\n\n n\n\n\n n\n\n\n ", type: "bot" });
    } catch (error) {
      console.error("Error calling LLM: ", error);
      messages.value.push({ text: "Error: Could not connect to the LLM.", type: "bot" });
    } finally {
      loading.value = false;
      scrollToBottom();
    }
  }
}

</script>
