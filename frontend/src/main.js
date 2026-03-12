import { createApp } from 'vue'
import './style.css'
import Chatbox from './Chatbox.vue'

export function createChatboxApp(targetElement, options) {
    const app = createApp(Chatbox);
    app.provide("projectId", options.project_id);
    app.provide("token", options.token ?? null);
    app.mount(targetElement);
}

const widgetAnchor = document.getElementById("vue-chatbox-widget");

if (widgetAnchor) {
    // If found, used through CakePHP. Start using data-attributes.
    createChatboxApp(widgetAnchor, { 
        project_id: widgetAnchor.dataset.projectId, 
        token: widgetAnchor.dataset.token 
    });
} 

// This is executed when the chatbox is run on its own (e.g. npm run dev).
else if (!window.parent || window === window.parent) {
    const targetElement = document.getElementById("app");
    createChatboxApp(targetElement, { project_id: 1, 
																			token: "" }); // Default 1 for evaluation without MMT front end integration.
}
