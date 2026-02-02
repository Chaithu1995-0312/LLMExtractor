# Jarvis Preview UI

A minimal, read-only preview interface for Recalled Bricks.

## Prerequisites

- Node.js (v14+)
- Python 3.8+ (for the backend)

## How to Run

1.  **Start the Backend**
    Ensure you are in the project root (`d:\chatgptdocs`):
    ```bash
    # Install backend dependencies if needed
    # pip install flask numpy faiss-cpu ...

    py backend/cortex/server.py or 
      py  -m backend/cortex/server
    ```
    The server should start on `http://localhost:5001`.

2.  **Start the Frontend**
    Open a new terminal in the project root:
    ```bash
    cd ui/jarvis
    npm install
    npm run dev
    ```
    The UI will start on `http://localhost:5173`.

3.  **Use the App**
    - Open `http://localhost:5173` in your browser.
    - Enter a query in the "Jarvis Preview" input (e.g., "nexus").
    - Click "Preview".
    - Click on a brick in the list to view details.

## Notes

-   **API Contract**: The UI strictly follows the `GET /jarvis/ask-preview` contract.
-   **Missing Metadata**: The current API returns only `brick_id` and `confidence`. The UI displays placeholders for `source_file`, `source_span`, and `text_sample` as they are not provided by the locked API.
