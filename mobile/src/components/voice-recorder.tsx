import { useRef, useState } from 'react';
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
  const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
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
  const [transcript, setTranscript] = useState<string | null>(null);
  const [hasUnsavedTranscript, setHasUnsavedTranscript] = useState(false);

  const operationInProgress = useRef(false);

  async function handlePlayback() {
    if (
        operationInProgress.current ||
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
    if (operationInProgress.current || isSavingNote) {
        return;
    }

    operationInProgress.current = true;
    setIsBusy(true);
    setErrorMessage(null);

    try {
    if (!recorder.isRecording && hasUnsavedTranscript) {
        const shouldDiscard = await confirmDiscardDraft();

        if (!shouldDiscard) {
        return;
        }
    }

    if (recorder.isRecording) {
        await recorder.stop();

        const uri = recorder.uri;

        if (!uri) {
            throw new Error('Không nhận được đường dẫn bản ghi.');
        }

        setRecordingUri(uri);

        await setAudioModeAsync({
            allowsRecording: false,
        });
        } else {
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

        setRecordingUri(null);
        setUploadMessage(null);
        setUploadError(null);
        setTranscript(null);
        setHasUnsavedTranscript(false);

        await recorder.prepareToRecordAsync();
        recorder.record();
        }
    } catch (error: unknown) {
        console.error('Lỗi thu âm:', error);

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
        operationInProgress.current ||
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
        }

        setUploadMessage(null);
        setUploadError(null);
        setTranscript(null);
        setHasUnsavedTranscript(false);

        const result = await transcribeRecording(recordingUri);
        const text = result.text.trim();

        if (text.length === 0) {
        setUploadMessage(
            'Không nhận dạng được lời nói trong bản ghi. ' +
            'Bạn có thể nghe lại hoặc thu một đoạn khác.',
        );
        return;
        }

        setTranscript(text);
        setHasUnsavedTranscript(true);

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

    const durationSeconds = Math.floor(
        recorderState.durationMillis / 1000,
    );

    const recordingDisabled =
    isBusy ||
    isUploading ||
    isSavingNote ||
    isPlaybackBusy;

    const uploadDisabled =
    isBusy ||
    isUploading ||
    isSavingNote ||
    isPlaybackBusy ||
    recorderState.isRecording ||
    recordingUri === null;

    const playbackDisabled =
    isBusy ||
    isPlaybackBusy ||
    recorderState.isRecording ||
    recordingUri === null ||
    !playerStatus.isLoaded;

  return (
    <View style={styles.card}>
      <Text style={styles.title}>Giọng nói — thử nghiệm thu âm</Text>

      <Text style={styles.status}>
        {recorderState.isRecording
          ? `Đang thu âm: ${durationSeconds} giây`
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

                {transcript !== null && (
                <TranscriptEditor
                    key={`${recordingUri ?? ''}:${transcript}`}
                    initialText={transcript}
                    disabled={
                        !storageReady ||
                        isSavingNote ||
                        isBusy ||
                        isUploading ||
                        recorderState.isRecording
                    }
                    onSave={onSaveTranscript}
                    onUnsavedChange={setHasUnsavedTranscript}
                />
                )}

                {uploadError !== null && (
                <Text accessibilityRole="alert" style={styles.error}>
                    {uploadError}
                </Text>
                )}
            </View>
        )}

        <Text style={styles.note}>
            Chỉ thu khi bạn bấm nút. Khi bấm “Chuyển thành văn bản”,
            audio sẽ được gửi qua backend tới Deepgram để nhận dạng.
            Chỉ thử bằng nội dung không nhạy cảm và giữ app mở trong lúc xử lý.
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