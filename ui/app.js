const treeEl = document.getElementById("tree");
const messagesEl = document.getElementById("messages");

// Example index.json you can auto-generate later
let rootHandle = null;

document.getElementById("openFolder").onclick = async () => {
  rootHandle = await window.showDirectoryPicker();
  loadIndex();
};

async function loadIndex() {
  const indexHandle = await rootHandle.getFileHandle("index.json");
  const file = await indexHandle.getFile();
  const text = await file.text();
  const data = JSON.parse(text);

  renderTree(data);
}

async function loadPath(relativePath) {
  const [folder, fileName] = relativePath.split("/");

  const convDir = await rootHandle.getDirectoryHandle(folder);
  const fileHandle = await convDir.getFileHandle(fileName);
  const file = await fileHandle.getFile();
  const text = await file.text();

  const data = JSON.parse(text);
  renderMessages(data.messages);
}


function renderTree(data) {
  const tree = document.getElementById("tree");
  tree.innerHTML = "";

  data.forEach(conv => {
    const li = document.createElement("li");
    li.textContent = conv.conversation_id;

    const ul = document.createElement("ul");

    conv.paths.forEach(p => {
      const pli = document.createElement("li");
      pli.textContent = p.label;
      pli.onclick = () => loadPath(p.file);
      ul.appendChild(pli);
    });

    li.appendChild(ul);
    tree.appendChild(li);
  });
}


function loadPath(file) {
  fetch(file)
    .then(res => res.json())
    .then(data => renderMessages(data.messages));
}



async function loadIndex() {
  const indexHandle = await rootHandle.getFileHandle("index.json");
  const file = await indexHandle.getFile();
  const text = await file.text();
  const data = JSON.parse(text);

  renderTree(data);
}

async function loadPath(relativePath) {
  const [folder, fileName] = relativePath.split("/");

  const convDir = await rootHandle.getDirectoryHandle(folder);
  const fileHandle = await convDir.getFileHandle(fileName);
  const file = await fileHandle.getFile();
  const text = await file.text();

  const data = JSON.parse(text);
  renderMessages(data.messages);
}

function renderMessages(messages) {
  messagesEl.innerHTML = "";

  messages.forEach(msg => {
    const div = document.createElement("div");
    div.className = `message ${msg.role}`;
    div.textContent = msg.text;
    messagesEl.appendChild(div);
  });
}
