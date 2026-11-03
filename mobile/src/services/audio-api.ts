import { fetch } from 'expo/fetch';
import { File } from 'expo-file-system';

export type AudioInspection = {
  status: 'received';
  filename: string | null;
  content_type: string | null;
  size_bytes: number;
};

function isAudioInspection(value: unknown): value is AudioInspection {
  if (typeof value !== 'object' || value === null) {
    return false;
  }

  return (
    'status' in value &&
    value.status === 'received' &&
    'filename' in value &&
    (typeof value.filename === 'string' || value.filename === null) &&
    'content_type' in value &&
    (typeof value.content_type === 'string' ||
      value.content_type === null) &&
    'size_bytes' in value &&
    typeof value.size_bytes === 'number' &&
    Number.isSafeInteger(value.size_bytes) &&
    value.size_bytes > 0
  );
}

export async function inspectAudio(
  uri: string,
): Promise<AudioInspection> {
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
  const timeoutId = setTimeout(() => controller.abort(), 30000);

  try {
    const response = await fetch(
      `${baseUrl.replace(/\/+$/, '')}/audio/inspect`,
      {
        method: 'POST',
        body: formData,
        signal: controller.signal,
      },
    );

    if (!response.ok) {
      throw new Error(`Upload thất bại: HTTP ${response.status}.`);
    }

    const data: unknown = await response.json();

    if (!isAudioInspection(data)) {
      throw new Error('Backend trả về dữ liệu kiểm tra audio không hợp lệ.');
    }

    return data;
  } finally {
    clearTimeout(timeoutId);
  }
}