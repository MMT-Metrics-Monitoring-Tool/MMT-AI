import { createApp } from 'vue'
import './style.css'
import Chatbox from './Chatbox.vue'

const DEFAULT_API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export function createChatboxApp(targetElement, options) {
    const app = createApp(Chatbox);
    app.provide("projectId", options.project_id);
    app.provide("token", options.token ?? null);
    app.provide("apiUrl", options.api_url || DEFAULT_API_URL);
    app.provide("refreshUrl", options.refresh_url || null);
    app.mount(targetElement);
}

const widgetAnchor = document.getElementById("vue-chatbox-widget");

if (widgetAnchor) {
    // If found, used through CakePHP. Start using data-attributes.
    createChatboxApp(widgetAnchor, { 
        project_id: widgetAnchor.dataset.projectId, 
        token: widgetAnchor.dataset.token,
        api_url: widgetAnchor.dataset.apiUrl,
        refresh_url: widgetAnchor.dataset.refreshUrl
    });
} 

// This is executed when the chatbox is run on its own (e.g. npm run dev).
else if (!window.parent || window === window.parent) {
    const targetElement = document.getElementById("app");
    createChatboxApp(targetElement, { project_id: 1, 
																			token: "" }); // Default 1 for evaluation without MMT front end integration.
}
