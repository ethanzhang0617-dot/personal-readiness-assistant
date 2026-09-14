/* Tiny dependency-free Streamlit ↔ IndexedDB bridge. */
const DB_NAME = "personal-readiness-assistant";
const DB_VERSION = 1;
const STORE_NAME = "app_state";
const STATE_KEY = "current";
let lastCommand = null;

function send(type, data = {}) {
  window.parent.postMessage({isStreamlitMessage: true, type, ...data}, "*");
}

function openDatabase() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) db.createObjectStore(STORE_NAME, {keyPath: "id"});
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error || new Error("IndexedDB could not be opened"));
  });
}

async function transact(mode, work) {
  const db = await openDatabase();
  try {
    return await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, mode);
      const store = tx.objectStore(STORE_NAME);
      let result;
      try { result = work(store); } catch (error) { reject(error); return; }
      tx.oncomplete = () => resolve(result && result.result);
      tx.onerror = () => reject(tx.error || new Error("IndexedDB transaction failed"));
      tx.onabort = () => reject(tx.error || new Error("IndexedDB transaction was aborted"));
    });
  } finally { db.close(); }
}

async function execute(args) {
  const commandId = String(args.command_id || "");
  if (!commandId || commandId === lastCommand) return;
  lastCommand = commandId;
  const status = document.getElementById("status");
  try {
    let state = null;
    if (args.operation === "load") {
      state = await transact("readonly", store => store.get(STATE_KEY));
      state = state ? state.state : null;
      status.textContent = state ? "Local browser history restored." : "No local browser history yet.";
    } else if (args.operation === "save") {
      await transact("readwrite", store => store.put({id: STATE_KEY, state: args.state}));
      status.textContent = "Saved locally in this browser.";
    } else if (args.operation === "clear") {
      await transact("readwrite", store => store.delete(STATE_KEY));
      status.textContent = "Local browser history cleared.";
    } else {
      throw new Error("Unsupported storage operation");
    }
    send("streamlit:setComponentValue", {value: {ok: true, operation: args.operation, command_id: commandId, state}});
  } catch (error) {
    status.textContent = "Local browser storage is unavailable.";
    send("streamlit:setComponentValue", {value: {ok: false, operation: args.operation, command_id: commandId, error: String(error && error.message || error)}});
  }
  send("streamlit:setFrameHeight", {height: 24});
}

window.addEventListener("message", event => {
  if (event.data && event.data.type === "streamlit:render") execute(event.data.args || {});
});
send("streamlit:componentReady", {apiVersion: 1});
send("streamlit:setFrameHeight", {height: 24});
