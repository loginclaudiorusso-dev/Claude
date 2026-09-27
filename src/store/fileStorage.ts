import { File, Paths } from 'expo-file-system';
import type { StateStorage } from 'zustand/middleware';

/**
 * zustand persistence backed by JSON files in the Documents directory. Used
 * for settings and profile data so nothing personal lands in AsyncStorage.
 */
const fileFor = (name: string) => new File(Paths.document, `${name}.json`);

/** Where the file system is unavailable (web), settings simply aren't persisted. */
export const fileStorage: StateStorage = {
  getItem: async (name) => {
    try {
      const f = fileFor(name);
      return f.exists ? await f.text() : null;
    } catch {
      return null;
    }
  },
  setItem: (name, value) => {
    try {
      const f = fileFor(name);
      if (!f.exists) f.create();
      f.write(value);
    } catch {
      // Not persisted on this platform.
    }
  },
  removeItem: (name) => {
    try {
      const f = fileFor(name);
      if (f.exists) f.delete();
    } catch {
      // Nothing stored.
    }
  },
};
