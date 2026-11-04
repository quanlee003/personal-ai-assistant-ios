import { useEffect, useRef, useState } from 'react';

import {
  clearTranscriptDraft,
  loadTranscriptDraft,
  saveTranscriptDraft,
} from '../services/transcript-draft-storage';

type DraftStatus = 'idle' | 'saving' | 'saved' | 'error';

export function useTranscriptDraft() {
  const [text, setText] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [status, setStatus] = useState<DraftStatus>('idle');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [cleanupRequired, setCleanupRequired] = useState(false);

  const revision = useRef(0);
  const actionInProgress = useRef(false);

  useEffect(() => {
    let ignore = false;

    async function restore() {
      try {
        const stored = await loadTranscriptDraft();

        if (ignore) {
          return;
        }

        setText(stored?.text ?? null);
        setStatus(stored === null ? 'idle' : 'saved');
        setReady(true);
      } catch (error: unknown) {
        if (ignore) {
          return;
        }

        console.error('Không thể đọc bản nháp:', error);
        setError(
          'Không đọc được bản nháp đã lưu. Tính năng thu và nhận dạng ' +
            'đang bị khóa để tránh ghi đè. Hãy reload app.',
        );
        setStatus('error');
      }
    }

    void restore();

    return () => {
      ignore = true;
    };
  }, []);

  function update(nextText: string) {
    if (!ready || actionInProgress.current || cleanupRequired) {
      return;
    }

    setText(nextText);
    setError(null);
    setStatus('saving');

    const currentRevision = ++revision.current;

    void saveTranscriptDraft(nextText).then(
      () => {
        if (revision.current === currentRevision) {
          setStatus('saved');
        }
      },
      (error: unknown) => {
        if (revision.current !== currentRevision) {
          return;
        }

        console.error('Không thể tự lưu bản nháp:', error);
        setStatus('error');
        setError(
          'Chưa lưu được thay đổi mới nhất của bản nháp. ' +
            'Đừng đóng app; hãy sửa tiếp hoặc bấm thử lưu lại.',
        );
      },
    );
  }

  async function discard(): Promise<boolean> {
    if (!ready || actionInProgress.current) {
      return false;
    }

    actionInProgress.current = true;
    setBusy(true);
    setError(null);
    ++revision.current;

    try {
      await clearTranscriptDraft();

      setText(null);
      setStatus('idle');
      setCleanupRequired(false);
      setError(null);

      return true;
    } catch (error: unknown) {
      console.error('Không thể xóa bản nháp:', error);
      setStatus('error');
      setError(
        cleanupRequired
          ? 'Ghi chú đã lưu, nhưng chưa dọn được bản nháp. ' +
              'Hãy thử dọn lại; không cần lưu ghi chú lần nữa.'
          : 'Chưa xóa được bản nháp. Nội dung vẫn được giữ trên màn hình.',
      );

      return false;
    } finally {
      actionInProgress.current = false;
      setBusy(false);
    }
  }

  async function saveAsNote(
    saveNote: () => Promise<boolean>,
  ): Promise<boolean> {
    if (
      !ready ||
      actionInProgress.current ||
      cleanupRequired ||
      text === null ||
      text.trim().length === 0
    ) {
      return false;
    }

    actionInProgress.current = true;
    setBusy(true);
    setError(null);

    // Không cho kết quả tự lưu cũ cập nhật trạng thái
    // trong lúc đang chuyển bản nháp thành ghi chú.
    ++revision.current;

    try {
    const success = await saveNote();

      if (!success) {
        setStatus('error');
        setError(
            'Chưa lưu được ghi chú. Bản nháp vẫn ở trên màn hình; ' +
            'hãy thử lưu ghi chú hoặc lưu lại bản nháp trước khi đóng app.',
        );
        return false;
      }

      // Từ đây ghi chú đã được lưu: không cho lưu trùng
      // chỉ vì thao tác dọn bản nháp bị lỗi.
      setCleanupRequired(true);
      ++revision.current;

      try {
        await clearTranscriptDraft();

        setText(null);
        setStatus('idle');
        setCleanupRequired(false);
        setError(null);
      } catch (error: unknown) {
        console.error('Ghi chú đã lưu nhưng chưa dọn được bản nháp:', error);
        setStatus('error');
        setError(
          'Ghi chú đã lưu thành công, nhưng chưa dọn được bản nháp. ' +
            'Bấm “Dọn bản nháp đã lưu”, không lưu ghi chú thêm lần nữa.',
        );
      }

      return true;
    } catch (error: unknown) {
      console.error('Không thể lưu ghi chú từ bản nháp:', error);
      setStatus('error');
      setError('Chưa lưu được ghi chú. Bản nháp vẫn được giữ lại.');
      return false;
    } finally {
      actionInProgress.current = false;
      setBusy(false);
    }
  }

  return {
    text,
    ready,
    status,
    error,
    busy,
    cleanupRequired,
    update,
    discard,
    saveAsNote,
  };
}