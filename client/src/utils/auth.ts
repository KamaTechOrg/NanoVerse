import type { User } from "../types/auth";

const TOKEN_KEY = "auth_token";
const USER_KEY = "auth_user";
const PLAYER_ID = "player_id"

// Fallback in-memory storage
const memoryStorage: Record<string, string> = {};

// Helper to detect if localStorage is available
function isLocalStorageAvailable(): boolean {
  try {
    const test = "__test__";
    localStorage.setItem(test, test);
    localStorage.removeItem(test);
    return true;
  } catch {
    return false;
  }
}

// Helper to detect if sessionStorage is available
function isSessionStorageAvailable(): boolean {
  try {
    const test = "__test__";
    sessionStorage.setItem(test, test);
    sessionStorage.removeItem(test);
    return true;
  } catch {
    return false;
  }
}

// Get the best available storage
function getStorage(): Storage | typeof memoryStorage {
  if (isLocalStorageAvailable()) {
    return localStorage;
  }
  if (isSessionStorageAvailable()) {
    return sessionStorage;
  }
  return memoryStorage as any;
}

const storage = getStorage();

export const authStorage = {
  getToken(): string | null {
    return storage.getItem(TOKEN_KEY);
  },

  setToken(token: string): void {
    storage.setItem(TOKEN_KEY, token);
  },

  removeToken(): void {
    storage.removeItem(TOKEN_KEY);
  },

  getUser(): User | null {
    const raw = storage.getItem(USER_KEY);
    try {
      return raw ? (JSON.parse(raw) as User) : null;
    } catch {
      return null;
    }
  },

  setUser(user: User): void {
    storage.setItem(USER_KEY, JSON.stringify(user));
  },

  setID(id: string): void {
    storage.setItem(PLAYER_ID, id);
  },

  removeUser(): void {
    storage.removeItem(USER_KEY);
  },

  clear(): void {
    this.removeToken();
    this.removeUser();
  },

  isAuthenticated(): boolean {
    return !!this.getToken() && !!this.getUser();
  },
};