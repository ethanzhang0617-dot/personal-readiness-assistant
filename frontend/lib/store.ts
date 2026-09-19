/**
 * Browser-local persistence for the user's own product data.
 *
 * IndexedDB is the product's established direction (the Streamlit V1.1 app used
 * the same store) and keeps check-ins, logged sessions, profile edits, post-session
 * feedback and chat on this device. State is kept per profile, so switching demo
 * profiles never mixes one profile's data into another. No remote database is
 * involved, and the API never stores any of this.
 *
 * Schema version 3 (V1.3) migrates older envelopes instead of resetting them; see
 * ``store-migration.ts`` for the mapping and the no-data-loss rules.
 */

import type { UserState } from "@/types/api";

import { migrateEnvelope, STORAGE_VERSION, type StoredEnvelope } from "@/lib/store-migration";

export { STORAGE_VERSION };
export type { StoredEnvelope };

/** Retained technical identifier (legacy project slug). Renaming it would orphan
 *  existing browser data, so the product-name migration deliberately keeps it. */
const DB_NAME = "personal-readiness-assistant";
const DB_VERSION = 1;
const STORE_NAME = "app-state";
const KEY = "user-state";

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

/** Read the stored envelope, migrating any older schema in place. */
export async function readEnvelope(): Promise<StoredEnvelope | null> {
  if (!isBrowser()) return null;
  try {
    const raw = await withStore<unknown>("readonly", (store) => store.get(KEY));
    if (!raw) return null;
    const migrated = migrateEnvelope(raw);
    if (!migrated) return null; // unknown or newer schema: leave it untouched
    if (migrated.report.migrated) {
      // Persist the upgraded shape immediately so the migration happens once.
      await withStore("readwrite", (store) => store.put(migrated.envelope, KEY));
    }
    return migrated.envelope;
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
