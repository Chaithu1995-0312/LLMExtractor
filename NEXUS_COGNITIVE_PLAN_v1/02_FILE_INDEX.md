# File Index — Nexus

src/nexus/
├── sync/
│   ├── runner.py
│   ├── state.json
├── index/
│   └── conversation_index.py
├── vector/
│   ├── embedder.py
│   └── local_index.py
├── ask/
│   └── recall.py
├── cognition/
│   ├── assembler.py
│   └── README.md
├── graph/
│   ├── manager.py
│   ├── nodes.json
│   └── edges.json

services/
└── cortex/
    └── server.py

output/
└── nexus/
    ├── artifacts/
    ├── conversation_index.json
    └── sync_state.json
