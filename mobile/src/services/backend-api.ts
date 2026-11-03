export async function checkBackendHealth(): Promise<void> {
  const baseUrl = process.env.EXPO_PUBLIC_API_BASE_URL?.trim();

  if (!baseUrl) {
    throw new Error('Chưa cấu hình EXPO_PUBLIC_API_BASE_URL.');
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 8000);

  try {
    const response = await fetch(
      `${baseUrl.replace(/\/+$/, '')}/health`,
      {
        signal: controller.signal,
      },
    );

    if (!response.ok) {
      throw new Error(`Backend trả về HTTP ${response.status}.`);
    }

    const data: unknown = await response.json();

    if (
      typeof data !== 'object' ||
      data === null ||
      !('status' in data) ||
      data.status !== 'ok'
    ) {
      throw new Error('Backend trả về dữ liệu health không đúng định dạng.');
    }
  } finally {
    clearTimeout(timeoutId);
  }
}