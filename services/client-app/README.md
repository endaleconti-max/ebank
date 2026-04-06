# client-app

Customer-facing web client for eBank transfer flows.

## Features
- Create transfer with sender, recipient phone, amount, currency, and note.
- List recent transfers with sender/status filters.
- View transfer details and event timeline.
- Cancel eligible transfers.

## Run locally
Start API gateway first (default: http://localhost:8000).

Then serve this folder from any static server.

Option 1 (Python):

```bash
cd services/client-app
python3 -m http.server 5173
```

Option 2 (Node):

```bash
cd services/client-app
npx serve -l 5173
```

Open http://localhost:5173

## API base URL
The UI defaults to `http://localhost:8000`. Override by adding `?apiBase=http://host:port` to the page URL.
