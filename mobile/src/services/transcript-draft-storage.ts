import AsyncStorage from '@react-native-async-storage/async-storage';

const TRANSCRIPT_DRAFT_KEY =
  '@personal-ai-assistant/transcript-draft/v1';

export type TranscriptDraft = {
  version: 1;
  text: string;
  updatedAt: string;
};

let operationQueue: Promise<void> = Promise.resolve();

function enqueue<T>(operation: () => Promise<T>): Promise<T> {
  const result = operationQueue.then(operation);

  // Lỗi vẫn được trả cho bên gọi, nhưng không làm kẹt hàng đợi.
  operationQueue = result.then(
    () => undefined,
    () => undefined,
  );

  return result;
}

function isTranscriptDraft(value: unknown): value is TranscriptDraft {
  if (typeof value !== 'object' || value === null) {
    return false;
  }

  return (
    'version' in value &&
    value.version === 1 &&
    'text' in value &&
    typeof value.text === 'string' &&
    'updatedAt' in value &&
    typeof value.updatedAt === 'string' &&
    value.updatedAt.trim().length > 0 &&
    Number.isFinite(Date.parse(value.updatedAt))
  );
}

export function loadTranscriptDraft(): Promise<TranscriptDraft | null> {
  return enqueue(async () => {
    const storedValue = await AsyncStorage.getItem(TRANSCRIPT_DRAFT_KEY);

    if (storedValue === null) {
      return null;
    }

    let parsedValue: unknown;

    try {
      parsedValue = JSON.parse(storedValue);
    } catch {
      throw new Error('Không đọc được định dạng bản nháp đã lưu.');
    }

    if (!isTranscriptDraft(parsedValue)) {
      throw new Error('Dữ liệu bản nháp đã lưu không hợp lệ.');
    }

    return parsedValue;
  });
}

export function saveTranscriptDraft(
  text: string,
): Promise<TranscriptDraft> {
  const draft: TranscriptDraft = {
    version: 1,
    text,
    updatedAt: new Date().toISOString(),
  };

  return enqueue(async () => {
    await AsyncStorage.setItem(
      TRANSCRIPT_DRAFT_KEY,
      JSON.stringify(draft),
    );

    return draft;
  });
}

export function clearTranscriptDraft(): Promise<void> {
  return enqueue(async () => {
    await AsyncStorage.removeItem(TRANSCRIPT_DRAFT_KEY);
  });
}