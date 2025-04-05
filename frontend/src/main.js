import { createApp } from 'vue'
import './style.css'
import Chatbox from './Chatbox.vue'

export function createChatboxApp(targetElement, options) {
    const app = createApp(Chatbox);
    app.provide("projectId", options.project_id);
    app.provide("token", options.token ?? null);
    app.mount(targetElement);
}

// This is executed when the chatbox is run on its own (e.g. npm run dev).
if (!window.parent || window === window.parent) {
    const targetElement = document.getElementById("app");
    createChatboxApp(targetElement, { project_id: 22, token: null }); // Default 22 for testing. (Esan testiprojekti)
}
