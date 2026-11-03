import AsyncStorage from '@react-native-async-storage/async-storage';

import type { Note } from '../types/note';

const NOTES_STORAGE_KEY = '@personal-ai-assistant/notes/v1';

function isNote(value: unknown): value is Note {
  if (typeof value !== 'object' || value === null) {
    return false;
  }

  return (
    'id' in value &&
    typeof value.id === 'string' &&
    value.id.trim().length > 0 &&
    'content' in value &&
    typeof value.content === 'string' &&
    value.content.trim().length > 0
  );
}

function isNoteArray(value: unknown): value is Note[] {
  if (!Array.isArray(value)) {
    return false;
  }

  const items: unknown[] = value;

  if (!items.every(isNote)) {
    return false;
  }

  const ids = items.map((note) => note.id);

  return new Set(ids).size === ids.length;
}

export async function loadNotes(): Promise<Note[]> {
  const storedValue = await AsyncStorage.getItem(NOTES_STORAGE_KEY);

  if (storedValue === null) {
    return [];
  }

  const parsedValue: unknown = JSON.parse(storedValue);

  if (!isNoteArray(parsedValue)) {
    throw new Error('Dữ liệu ghi chú đã lưu không hợp lệ.');
  }

  return parsedValue;
}

export async function saveNotes(notes: Note[]): Promise<void> {
  if (!isNoteArray(notes)) {
    throw new Error('Không thể lưu danh sách ghi chú không hợp lệ.');
  }

  const serializedValue = JSON.stringify(notes);

  await AsyncStorage.setItem(NOTES_STORAGE_KEY, serializedValue);
}