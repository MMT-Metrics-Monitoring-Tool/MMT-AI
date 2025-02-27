<script>
import { ref } from "vue";

export default {
  setup() {
    const messages = ref([
      { text: "Hello! How can I help you?", type: "bot" },
    ]);
    const input = ref("");

    const sendMessage = () => {
      if (input.value.trim()) {
        messages.value.push({ text: input.value, type: "user" });
        input.value = "";
        setTimeout(() => {
          messages.value.push({ text: "Heehee", type: "bot" }); // Sample response after message.
        }, 1000);
      }
    };

    return { messages, input, sendMessage };
  }
}
</script>

<template>
  <div class="chatbox">
    <div class="messages">
      <div v-for="(msg, index) in messages" :key="index" :class="['message', msg.type]">
        {{ msg.text }}
      </div>
    </div>
    <div class="input-area">
      <input v-model="input" @keydown.enter="sendMessage" placeholder="Type a message" />
      <button @click="sendMessage">Send</button>
    </div>
  </div>
</template>
