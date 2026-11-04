import { useEffect, useRef, useState } from 'react';
import {
  Alert,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import {
  AudioModule,
  RecordingPresets,
  setAudioModeAsync,
  useAudioPlayer,
  useAudioPlayerStatus,
  useAudioRecorder,
  useAudioRecorderState,
} from 'expo-audio';

import RecordingPlayer from './recording-player';
import { transcribeRecording } from '../services/transcription-api';
import TranscriptEditor from './transcript-editor';
import { useTranscriptDraft } from '../hooks/use-transcript-draft';

const MAX_RECORDING_SECONDS = 60;

type RecordingCompletion = {
  uri: string | null;
  error: string | null;
};

function confirmDiscardDraft(): Promise<boolean> {
  return new Promise((resolve) => {
    Alert.alert(
      'Bản nháp chưa được lưu',
      'Tiếp tục sẽ bỏ văn bản đang chỉnh sửa. Bạn muốn làm gì?',
      [
        {
          text: 'Giữ bản nháp',
          style: 'cancel',
          onPress: () => resolve(false),
        },
        {
          text: 'Bỏ bản nháp',
          style: 'destructive',
          onPress: () => resolve(true),
        },
      ],
      {
        cancelable: false,
      },
    );
  });
}

type VoiceRecorderProps = {
  storageReady: boolean;
  isSavingNote: boolean;
  onSaveTranscript: (text: string) => Promise<boolean>;
};

export default function VoiceRecorder({
  storageReady,
  isSavingNote,
  onSaveTranscript,
}: VoiceRecorderProps) {
    const recordingSessionActive = useRef(false);

    const [pendingCompletion, setPendingCompletion] =
    useState<RecordingCompletion | null>(null);

    const recorder = useAudioRecorder(
    RecordingPresets.HIGH_QUALITY,
    (status) => {
        if (!recordingSessionActive.current) {
        return;
        }

        if (status.hasError) {
        setPendingCompletion({
            uri: null,
            error: status.error ?? 'Recorder báo lỗi trong khi thu âm.',
        });
        return;
        }

        if (status.isFinished) {
        setPendingCompletion({
            uri: status.url,
            error: null,
        });
        }
    },
    );

    const recorderState = useAudioRecorderState(recorder);

  const [isBusy, setIsBusy] = useState(false);
  const [recordingUri, setRecordingUri] = useState<string | null>(null);
  const player = useAudioPlayer(recordingUri);
  const playerStatus = useAudioPlayerStatus(player);

  const [isPlaybackBusy, setIsPlaybackBusy] = useState(false);
  const [playbackError, setPlaybackError] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [isUploading, setIsUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const draft = useTranscriptDraft();

  const transcript = draft.text;

  const hasUnsavedTranscript =
    transcript !== null && !draft.cleanupRequired;

  const operationInProgress = useRef(false);

  useEffect(() => {
    if (
        pendingCompletion === null ||
        isBusy ||
        operationInProgress.current ||
        !recordingSessionActive.current
    ) {
        return;
    }

    // Nhận quyền hoàn tất đúng một lần cho phiên hiện tại.
    recordingSessionActive.current = false;
    operationInProgress.current = true;
    setIsBusy(true);

    async function finalizeRecording() {
        try {
        if (pendingCompletion === null) {
            return;
        }

        if (pendingCompletion.error !== null) {
            throw new Error(pendingCompletion.error);
        }

        const uri = pendingCompletion.uri ?? recorder.uri;

        if (!uri) {
            throw new Error('Không nhận được đường dẫn bản ghi.');
        }

        setRecordingUri(uri);
        } catch (error: unknown) {
        console.error('Không thể hoàn tất bản ghi:', error);

        setErrorMessage(
            'Không hoàn tất được bản ghi. Hãy thử thu lại một đoạn ngắn.',
        );
        } finally {
        try {
            await setAudioModeAsync({
            allowsRecording: false,
            playsInSilentMode: true,
            shouldPlayInBackground: false,
            });
        } catch (error: unknown) {
            console.error('Không thể khôi phục audio mode:', error);

            setErrorMessage(
            'Đã kết thúc xử lý bản ghi nhưng chưa khôi phục được audio mode. ' +
                'Hãy thử phát lại; nếu vẫn lỗi, mở lại app.',
            );
        } finally {
            setPendingCompletion(null);
            setIsBusy(false);
            operationInProgress.current = false;
        }
        }
    }

    void finalizeRecording();
    }, [pendingCompletion, isBusy, recorder]);

  async function handlePlayback() {
    if (
        operationInProgress.current ||
        pendingCompletion !== null ||
        recordingSessionActive.current ||
        recorder.isRecording ||
        !recordingUri ||
        !player.isLoaded
        ) {
        return;
    }

    operationInProgress.current = true;
    setIsPlaybackBusy(true);
    setPlaybackError(null);

    try {
        if (player.playing) {
        player.pause();
        } else {
        await setAudioModeAsync({
            allowsRecording: false,
            playsInSilentMode: true,
            shouldPlayInBackground: false,
        });

        await player.seekTo(0);
        player.play();
        }
    } catch (error: unknown) {
        console.error('Không thể phát bản ghi:', error);

        setPlaybackError(
        'Không thể phát bản ghi. Hãy thử lại hoặc thu một đoạn mới.',
        );
    } finally {
        setIsPlaybackBusy(false);
        operationInProgress.current = false;
    }
    }

  async function handleToggleRecording() {
    if (
        !draft.ready ||
        draft.busy ||
        draft.cleanupRequired ||
        operationInProgress.current || 
        isSavingNote ||
        pendingCompletion !== null
    ) {
        return;
    }

    operationInProgress.current = true;
    setIsBusy(true);
    setErrorMessage(null);

    try {
        if (recorder.isRecording) {
        await recorder.stop();

        // Dự phòng cho đường dừng thủ công:
        // không phụ thuộc hoàn toàn vào thời điểm callback native tới.
        if (recordingSessionActive.current) {
            setPendingCompletion({
            uri: recorder.uri,
            error: null,
            });
        }

        return;
        }

        // Recorder có thể vừa tự dừng nhưng callback chưa được xử lý.
        // Không bắt đầu phiên mới trước khi hoàn tất phiên cũ.
        if (recordingSessionActive.current) {
        return;
        }

        if (hasUnsavedTranscript) {
            const shouldDiscard = await confirmDiscardDraft();

            if (!shouldDiscard) {
                return;
            }

            const discarded = await draft.discard();

            if (!discarded) {
                return;
            }
        }

        const permission =
        await AudioModule.requestRecordingPermissionsAsync();

        if (!permission.granted) {
        setErrorMessage(
            'Chưa có quyền microphone. Nếu đã từ chối quyền, ' +
            'hãy kiểm tra quyền microphone của Expo Go trong Settings.',
        );
        return;
        }

        if (player.isLoaded) {
        player.pause();
        }

        setPlaybackError(null);

        await setAudioModeAsync({
        allowsRecording: true,
        playsInSilentMode: true,
        allowsBackgroundRecording: false,
        shouldPlayInBackground: false,
        });

        await recorder.prepareToRecordAsync();

        setRecordingUri(null);
        setUploadMessage(null);
        setUploadError(null);

        recordingSessionActive.current = true;

        recorder.record({
        forDuration: MAX_RECORDING_SECONDS,
        });
    } catch (error: unknown) {
        console.error('Lỗi thu âm:', error);

        if (!recorder.isRecording) {
        recordingSessionActive.current = false;

        try {
            await setAudioModeAsync({
            allowsRecording: false,
            playsInSilentMode: true,
            shouldPlayInBackground: false,
            });
        } catch (modeError: unknown) {
            console.error('Không thể khôi phục audio mode:', modeError);
        }
        }

        setErrorMessage(
        'Thao tác thu âm gặp lỗi. Hãy kiểm tra trạng thái bên dưới ' +
            'và dừng thu nếu ứng dụng vẫn đang ghi âm.',
        );
    } finally {
        setIsBusy(false);
        operationInProgress.current = false;
    }
    }

    async function handleUpload() {
    if (
        !draft.ready ||
        draft.busy ||
        draft.cleanupRequired ||
        operationInProgress.current ||
        pendingCompletion !== null ||
        recordingSessionActive.current ||
        isSavingNote ||
        recorder.isRecording ||
        !recordingUri
    ) {
        return;
    }

    operationInProgress.current = true;
    setIsUploading(true);

    try {
        if (hasUnsavedTranscript) {
            const shouldDiscard = await confirmDiscardDraft();

            if (!shouldDiscard) {
                return;
            }

            const discarded = await draft.discard();

            if (!discarded) {
                return;
            }
        }

        setUploadMessage(null);
        setUploadError(null);

        const result = await transcribeRecording(recordingUri);
        const text = result.text.trim();

        if (text.length === 0) {
        setUploadMessage(
            'Không nhận dạng được lời nói trong bản ghi. ' +
            'Bạn có thể nghe lại hoặc thu một đoạn khác.',
        );
        return;
        }

        draft.update(text);

        setUploadMessage(
        'Đã nhận văn bản. Hãy kiểm tra nội dung trước khi sử dụng.',
        );
    } catch (error: unknown) {
        console.error('Lỗi chuyển audio thành văn bản:', error);

        const wasAborted =
        error instanceof Error && error.name === 'AbortError';

        setUploadError(
        wasAborted
            ? 'Đã hết thời gian chờ. Backend có thể vẫn đang xử lý. ' +
                'Không tự động gửi lại để tránh tạo request trùng.'
            : error instanceof Error
            ? error.message
            : 'Không chuyển được audio thành văn bản. ' +
                'Hãy kiểm tra kết nối và thử lại.',
        );
    } finally {
        setIsUploading(false);
        operationInProgress.current = false;
    }
    }
    async function handleSaveDraft(text: string): Promise<boolean> {
    if (
        operationInProgress.current ||
        recorder.isRecording ||
        pendingCompletion !== null ||
        isSavingNote
    ) {
        return false;
    }

    operationInProgress.current = true;

    try {
        return await draft.saveAsNote(() => onSaveTranscript(text));
    } finally {
        operationInProgress.current = false;
    }
    }

    async function handleDiscardDraft() {
    if (
        operationInProgress.current ||
        draft.busy ||
        !draft.ready ||
        recorder.isRecording ||
        pendingCompletion !== null ||
        isSavingNote
    ) {
        return;
    }

    operationInProgress.current = true;

    try {
        if (!draft.cleanupRequired) {
        const confirmed = await confirmDiscardDraft();

        if (!confirmed) {
            return;
        }
        }

        await draft.discard();
    } finally {
        operationInProgress.current = false;
    }
    }

    const durationSeconds = Math.min(
    MAX_RECORDING_SECONDS,
    Math.floor(recorderState.durationMillis / 1000),
    );

    const isFinalizingRecording = pendingCompletion !== null;

    const recordingDisabled =
    !draft.ready ||
    draft.busy ||
    draft.cleanupRequired ||
    isBusy ||
    isUploading ||
    isSavingNote ||
    isPlaybackBusy ||
    isFinalizingRecording;

    const uploadDisabled =
    !draft.ready ||
    draft.busy ||
    draft.cleanupRequired ||
    isBusy ||
    isUploading ||
    isSavingNote ||
    isPlaybackBusy ||
    isFinalizingRecording ||
    recorderState.isRecording ||
    recordingUri === null;

    const playbackDisabled =
    isBusy ||
    isPlaybackBusy ||
    isFinalizingRecording ||
    recorderState.isRecording ||
    recordingUri === null ||
    !playerStatus.isLoaded;

  return (
    <View style={styles.card}>
      <Text style={styles.status}>
        {isFinalizingRecording
            ? 'Đang hoàn tất bản ghi...'
            : recorderState.isRecording
            ? `Đang thu âm: ${durationSeconds} / ${MAX_RECORDING_SECONDS} giây`
            : recordingUri !== null
                ? 'Đã có bản ghi — có thể nghe lại hoặc chuyển thành văn bản.'
                : 'Không thu âm'}
        </Text>

      <Pressable
        accessibilityRole="button"
        accessibilityState={{ disabled: recordingDisabled }}
        disabled={recordingDisabled}
        onPress={handleToggleRecording}
        style={({ pressed }) => [
            styles.button,
            recorderState.isRecording && styles.stopButton,
            (pressed || recordingDisabled) && styles.dimmed,
        ]}
        >
        <Text style={styles.buttonText}>
        {isUploading
            ? 'Đang nhận dạng...'
            : isFinalizingRecording
            ? 'Đang hoàn tất...'
            : isBusy || isPlaybackBusy
                ? 'Đang xử lý...'
                : recorderState.isRecording
                ? 'Dừng thu âm'
                : 'Bắt đầu thu âm'}
        </Text>
        </Pressable>

      {errorMessage !== null && (
        <Text accessibilityRole="alert" style={styles.error}>
          {errorMessage}
        </Text>
      )}

        {recordingUri !== null && (
            <View style={styles.recordingInfo}>
                <Text style={styles.text}>Đã nhận đường dẫn bản ghi:</Text>

                <Text selectable style={styles.uri}>
                {recordingUri}
                </Text>

                <RecordingPlayer
                isLoaded={playerStatus.isLoaded}
                isPlaying={playerStatus.playing}
                isBusy={isPlaybackBusy}
                disabled={playbackDisabled}
                currentTime={playerStatus.currentTime}
                duration={playerStatus.duration}
                errorMessage={playbackError}
                onTogglePlayback={handlePlayback}
                />

                <Pressable
                accessibilityRole="button"
                accessibilityState={{
                    disabled: uploadDisabled,
                    busy: isUploading,
                }}
                disabled={uploadDisabled}
                onPress={handleUpload}
                style={({ pressed }) => [
                    styles.button,
                    (pressed || uploadDisabled) && styles.dimmed,
                ]}
                >
                <Text style={styles.buttonText}>
                    {isUploading ? 'Đang nhận dạng...' : 'Chuyển thành văn bản'}
                </Text>
                </Pressable>

                {uploadMessage !== null && (
                <Text accessibilityLiveRegion="polite" style={styles.status}>
                    {uploadMessage}
                    
                </Text>
                )}

                

                {uploadError !== null && (
                <Text accessibilityRole="alert" style={styles.error}>
                    {uploadError}
                </Text>
                )}
            </View>
        )}
        
        {!draft.ready && draft.error === null && (
            <Text style={styles.note}>Đang đọc bản nháp...</Text>
            )}

            {draft.error !== null && (
            <Text accessibilityRole="alert" style={styles.error}>
                {draft.error}
            </Text>
            )}

            {transcript !== null && (
            <View style={styles.recordingInfo}>
                <Text accessibilityLiveRegion="polite" style={styles.note}>
                {draft.cleanupRequired
                    ? 'Ghi chú đã lưu; đang chờ dọn bản nháp.'
                    : draft.status === 'saving'
                    ? 'Đang lưu bản nháp...'
                    : draft.status === 'saved'
                        ? 'Đã lưu bản nháp trên thiết bị.'
                        : draft.status === 'error'
                        ? 'Bản nháp chưa được xác nhận lưu.'
                        : 'Bản nháp văn bản'}
                </Text>

                <TranscriptEditor
                value={transcript}
                disabled={
                    !storageReady ||
                    !draft.ready ||
                    draft.busy ||
                    draft.cleanupRequired ||
                    isSavingNote ||
                    isBusy ||
                    isUploading ||
                    isPlaybackBusy ||
                    isFinalizingRecording ||
                    recorderState.isRecording
                }
                onSave={handleSaveDraft}
                onTextChange={draft.update}
                />

                {draft.status === 'error' && !draft.cleanupRequired && draft.ready && (
                <Pressable
                    accessibilityRole="button"
                    disabled={draft.busy || isBusy || isUploading || isSavingNote}
                    onPress={() => draft.update(transcript)}
                    style={styles.button}
                >
                    <Text style={styles.buttonText}>Thử lưu lại bản nháp</Text>
                </Pressable>
                )}

                <Pressable
                accessibilityRole="button"
                disabled={
                    draft.busy ||
                    isBusy ||
                    isUploading ||
                    isSavingNote ||
                    isPlaybackBusy ||
                    isFinalizingRecording ||
                    recorderState.isRecording
                }
                onPress={handleDiscardDraft}
                style={styles.button}
                >
                <Text style={styles.buttonText}>
                    {draft.cleanupRequired
                    ? 'Dọn bản nháp đã lưu'
                    : 'Bỏ bản nháp'}
                </Text>
                </Pressable>
            </View>
        )}

        <Text style={styles.note}>
        Mỗi bản ghi tối đa {MAX_RECORDING_SECONDS} giây và tự dừng khi
        đạt giới hạn. Audio chỉ được gửi qua backend tới Deepgram khi
        bạn bấm “Chuyển thành văn bản”. Chỉ thử bằng nội dung không
        nhạy cảm và giữ app mở trong lúc thu, xử lý.
        </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#1E293B',
    borderRadius: 20,
    padding: 20,
    gap: 16,
  },
  title: {
    color: '#F8FAFC',
    fontSize: 18,
    fontWeight: '600',
  },
  status: {
    color: '#5EEAD4',
    fontSize: 16,
    lineHeight: 24,
  },
  button: {
    backgroundColor: '#5EEAD4',
    paddingVertical: 16,
    paddingHorizontal: 20,
    borderRadius: 12,
    alignItems: 'center',
  },
  stopButton: {
    backgroundColor: '#FDA4AF',
  },
  dimmed: {
    opacity: 0.6,
  },
  buttonText: {
    color: '#0B1120',
    fontSize: 16,
    fontWeight: '700',
  },
  recordingInfo: {
    gap: 8,
  },
  text: {
    color: '#CBD5E1',
    fontSize: 14,
  },
  uri: {
    color: '#94A3B8',
    fontSize: 12,
    lineHeight: 18,
  },
  note: {
    color: '#94A3B8',
    fontSize: 13,
    lineHeight: 20,
  },
  error: {
    color: '#FCA5A5',
    fontSize: 14,
    lineHeight: 22,
  },
});