# Chat widget

Vue 3 widget that MMT shows on the project dashboard. Answers are streamed from the backend as server-sent events (`src/sse.js`) and rendered as sanitized Markdown.

| File | Description |
| --- | --- |
| `src/main.js` | Mounts the widget and reads its settings from MMT's data attributes |
| `src/Chatbox.vue` | The chat UI, requests to the backend and token renewal |
| `src/categorizedQuestions.json` | Quick questions shown as buttons, by category |

## Settings from MMT

MMT renders an element with these data attributes, and the widget mounts into it:

```html
<div id="vue-chatbox-widget"
    data-project-id="12"
    data-token="<chatbot JWT signed by MMT>"
    data-api-url="https://mmt.example.fi/ai"
    data-refresh-url="/chatbot/refresh-token">
</div>
```

| Attribute | Description |
| --- | --- |
| `data-project-id` | Project the questions are about |
| `data-token` | Chatbot token signed by MMT, see the token contract in [backend/README.md](../backend/README.md) |
| `data-api-url` | Backend address as seen by the browser. Not MMT's internal Docker address (`http://mmt-backend:8000`), which browsers cannot reach. |
| `data-refresh-url` | MMT page that returns `{"token": "..."}` for the logged-in user |

## Token renewal

When the backend answers 401, the widget gets a new token and sends the same request once more, so the user does not have to ask again.

- **Inside MMT** the new token comes from `data-refresh-url`. The request sends the MMT login cookie, so MMT can check the user's login and project membership. If MMT refuses (403), returns its login page instead of JSON, or the retry also fails, the widget shows "Your session has ended. Please reload the page."
- **On its own** (no `data-refresh-url`) the token comes from the backend's `/start_session`, both on start and on renewal. This needs `AUTH_DEV_MODE=true` in the backend. When dev mode is off, the widget says so.

## Development

Start the backend first, with `AUTH_DEV_MODE=true` in `.env`. Then:

```sh
npm install
npm run dev          # http://localhost:5173
```

On its own the widget uses project 1 and the backend at `VITE_API_URL`, or `http://localhost:8000` when it is not set (e.g. `VITE_API_URL=http://localhost:8001 npm run dev`).

## Tests

```sh
npm run test:run     # once
npm test             # watch mode
```

## Build and deploy to MMT

```sh
npm run build
```

Copy the contents of `dist/` to `webroot/js/mmt-ai-vue-widget/` in MMT. MMT loads `index.js` and `index.css` from there. Deploy the new build together with any MMT template change it depends on, such as new data attributes.
