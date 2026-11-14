import type { ReportDraft } from "./draft";

/**
 * Where an in-progress report is kept on the device. Drafts must survive a
 * reload, a closed tab or a dropped connection, so the default store is
 * IndexedDB (which can hold the photos as Blobs). Where IndexedDB is not
 * available (some private-browsing modes), drafts live in memory only and
 * the UI says so.
 */
export interface DraftStore {
  readonly persistent: boolean;
  load(): Promise<ReportDraft | null>;
  save(draft: ReportDraft): Promise<void>;
  clear(): Promise<void>;
}

export class MemoryDraftStore implements DraftStore {
  readonly persistent = false;
  private draft: ReportDraft | null = null;

  async load() {
    return this.draft;
  }

  async save(draft: ReportDraft) {
    this.draft = draft;
  }

  async clear() {
    this.draft = null;
  }
}

const DB_NAME = "civicwatch";
const STORE = "report-drafts";
const KEY = "current";

function request<T>(req: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

class IndexedDbDraftStore implements DraftStore {
  readonly persistent = true;

  constructor(private readonly db: IDBDatabase) {}

  static async open(): Promise<IndexedDbDraftStore> {
    const open = indexedDB.open(DB_NAME, 1);
    open.onupgradeneeded = () => open.result.createObjectStore(STORE);
    return new IndexedDbDraftStore(await request(open));
  }

  private store(mode: IDBTransactionMode) {
    return this.db.transaction(STORE, mode).objectStore(STORE);
  }

  async load() {
    const draft = (await request(this.store("readonly").get(KEY))) as ReportDraft | undefined;
    return draft && draft.version === 1 ? draft : null;
  }

  async save(draft: ReportDraft) {
    await request(this.store("readwrite").put(draft, KEY));
  }

  async clear() {
    await request(this.store("readwrite").delete(KEY));
  }
}

export async function openDraftStore(): Promise<DraftStore> {
  if (typeof indexedDB === "undefined") return new MemoryDraftStore();
  try {
    return await IndexedDbDraftStore.open();
  } catch {
    return new MemoryDraftStore();
  }
}
