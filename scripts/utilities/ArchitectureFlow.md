To sync your new `conversations.json` and use it in the UI, you need to execute the following sequence of commands. This process involves three main steps: ingestion (Sync), serving the API (Backend), and launching the interface (UI).

### 1. Ingest and Sync Data
Run the sync command from the project root. This processes `conversations.json`, extracts "bricks" (content units), builds "walls" (context windows), and updates the vector index in `output/nexus`.

```bash
py nexus-cli/__main__.py sync
```

### 2. Start the Cortex Backend API
Launch the Flask server that serves the processed data. This API allows the UI to query the bricks and walls you just generated. Open a **new terminal** for this, as it needs to stay running.

```bash
py backend/cortex/server.py
```
*Note: This server runs on `http://localhost:5001`.*

### 3. Launch the Jarvis UI
Start the frontend development server. Open a **third terminal** for this.

```bash
cd ui/jarvis
npm run dev
```
*Note: If this is your first time running the UI, you may need to run `npm install` before `npm run dev`.*

### Summary of Workflow
1.  **Sync**: `conversations.json` -> `nexus-cli` -> `output/nexus` (Index & Bricks)
2.  **Backend**: `output/nexus` -> `server.py` (API Endpoint)
3.  **UI**: User -> `localhost:5173` (UI) -> `localhost:5001` (API)

Once all three are running, open the URL provided by the UI command (typically `http://localhost:5173`) in your browser to interact with your data.