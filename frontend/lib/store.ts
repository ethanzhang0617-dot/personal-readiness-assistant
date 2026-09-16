/**
 * Browser-local persistence for the user's own product data.
 *
 * IndexedDB is the product's established direction (the Streamlit V1.1 app used
 * the same store) and keeps check-ins, logged sessions, profile edits and chat on
 * this device. State is kept per profile, so switching demo profiles never mixes
 * one profile's data into another. No remote database is involved, and the API
 * never stores any of this.
 */

import type { UserState } from "@/types/api";

const DB_NAME = "personal-readiness-assistant";
const DB_VERSION = 1;
const STORE_NAME = "app-state";
const KEY = "user-state";

export const STORAGE_VERSION = 2;

export interface StoredEnvelope {
  version: number;
  updated_at: string;
  active_profile_id: string;
  states: Record<string, UserState>;
  chats: Record<string, unknown[]>;
}

function isBrowser(): boolean {
  return typeof window !== "undefined" && typeof window.indexedDB !== "undefined";
}

function openDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = window.indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const database = request.result;
      if (!database.objectStoreNames.contains(STORE_NAME)) {
        database.createObjectStore(STORE_NAME);
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error ?? new Error("IndexedDB could not be opened"));
  });
}

async function withStore<T>(mode: IDBTransactionMode, run: (store: IDBObjectStore) => IDBRequest): Promise<T> {
  const database = await openDatabase();
  return new Promise<T>((resolve, reject) => {
    const transaction = database.transaction(STORE_NAME, mode);
    const request = run(transaction.objectStore(STORE_NAME));
    request.onsuccess = () => resolve(request.result as T);
    request.onerror = () => reject(request.error ?? new Error("IndexedDB request failed"));
    transaction.oncomplete = () => database.close();
    transaction.onabort = () => reject(transaction.error ?? new Error("IndexedDB transaction aborted"));
  });
}

export async function readEnvelope(): Promise<StoredEnvelope | null> {
  if (!isBrowser()) return null;
  try {
    const value = await withStore<StoredEnvelope | undefined>("readonly", (store) => store.get(KEY));
    if (!value || typeof value !== "object" || !value.states) return null;
    if (value.version !== STORAGE_VERSION) return null; // incompatible schema: reseed
    return value;
  } catch {
    // Private mode or a blocked store must not break the app.
    return null;
  }
}

export async function writeEnvelope(
  activeProfileId: string,
  states: Record<string, UserState>,
  chats: Record<string, unknown[]>,
): Promise<boolean> {
  if (!isBrowser()) return false;
  const envelope: StoredEnvelope = {
    version: STORAGE_VERSION,
    updated_at: new Date().toISOString(),
    active_profile_id: activeProfileId,
    states,
    chats,
  };
  try {
    await withStore("readwrite", (store) => store.put(envelope, KEY));
    return true;
  } catch {
    return false;
  }
}

export async function clearEnvelope(): Promise<void> {
  if (!isBrowser()) return;
  try {
    await withStore("readwrite", (store) => store.delete(KEY));
  } catch {
    /* nothing to recover from */
  }
}
