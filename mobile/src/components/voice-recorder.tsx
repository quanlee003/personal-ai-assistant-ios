import { useRef, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import {
  AudioModule,
  RecordingPresets,
  setAudioModeAsync,
  useAudioRecorder,
  useAudioRecorderState,
} from 'expo-audio';

import RecordingPlayer from './recording-player';

export default function VoiceRecorder() {
  const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
  const recorderState = useAudioRecorderState(recorder);

  const [isBusy, setIsBusy] = useState(false);
  const [recordingUri, setRecordingUri] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const operationInProgress = useRef(false);

  async function handleToggleRecording() {
    if (operationInProgress.current) {
      return;
    }

    operationInProgress.current = true;
    setIsBusy(true);
    setErrorMessage(null);

    try {
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

        await setAudioModeAsync({
          allowsRecording: true,
          playsInSilentMode: true,
          allowsBackgroundRecording: false,
        });

        if (!permission.granted) {
            setErrorMessage(
                'Chưa có quyền microphone. Nếu đã từ chối quyền, ' +
                'hãy kiểm tra quyền microphone của Expo Go trong Settings.',
            );
            return;
        }

        setRecordingUri(null);

        await setAudioModeAsync({
            allowsRecording: true,
            playsInSilentMode: true,
            allowsBackgroundRecording: false,
        });

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

  const durationSeconds = Math.floor(
    recorderState.durationMillis / 1000,
  );

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
        accessibilityState={{ disabled: isBusy }}
        disabled={isBusy}
        onPress={handleToggleRecording}
        style={({ pressed }) => [
          styles.button,
          recorderState.isRecording && styles.stopButton,
          (pressed || isBusy) && styles.dimmed,
        ]}
      >
        <Text style={styles.buttonText}>
          {isBusy
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

            <RecordingPlayer key={recordingUri} uri={recordingUri} />
        </View>
        )}

      <Text style={styles.note}>
        Chỉ thu khi bạn bấm nút. Chưa gửi audio ra ngoài,
        chưa chuyển thành văn bản. Giữ app mở trong lúc thử.
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