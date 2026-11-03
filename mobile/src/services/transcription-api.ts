import { fetch } from 'expo/fetch';
import { File } from 'expo-file-system';

export type TranscriptionResult = {
  text: string;
  engine: 'deepgram' | 'apple';
};

function isTranscriptionResult(
  value: unknown,
): value is TranscriptionResult {
  return (
    typeof value === 'object' &&
    value !== null &&
    'text' in value &&
    typeof value.text === 'string' &&
    'engine' in value &&
    (value.engine === 'deepgram' || value.engine === 'apple')
  );
}

function getErrorDetail(value: unknown): string | null {
  if (
    typeof value === 'object' &&
    value !== null &&
    'detail' in value &&
    typeof value.detail === 'string'
  ) {
    return value.detail;
  }

  return null;
}

export async function transcribeRecording(
  uri: string,
): Promise<TranscriptionResult> {
  const baseUrl = process.env.EXPO_PUBLIC_API_BASE_URL?.trim();

  if (!baseUrl) {
    throw new Error('Chưa cấu hình EXPO_PUBLIC_API_BASE_URL.');
  }

  const file = new File(uri);

  if (!file.exists) {
    throw new Error('File bản ghi không còn tồn tại. Hãy thu lại.');
  }

  if (file.size === 0) {
    throw new Error('File bản ghi không có dữ liệu.');
  }

  if (file.size > 10 * 1024 * 1024) {
    throw new Error('File bản ghi vượt giới hạn 10 MiB.');
  }

  const formData = new FormData();
  formData.append('file', file);

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 90000);

  try {
    const response = await fetch(
      `${baseUrl.replace(/\/+$/, '')}/audio/transcribe`,
      {
        method: 'POST',
        body: formData,
        signal: controller.signal,
      },
    );

    const data: unknown = await response.json().catch(() => null);

    if (!response.ok) {
      throw new Error(
        getErrorDetail(data) ??
          `Nhận dạng thất bại: HTTP ${response.status}.`,
      );
    }

    if (!isTranscriptionResult(data)) {
      throw new Error('Backend trả về dữ liệu transcript không hợp lệ.');
    }

    return data;
  } finally {
    clearTimeout(timeoutId);
  }
}