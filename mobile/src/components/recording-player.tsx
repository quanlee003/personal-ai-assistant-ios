import { useRef, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import {
  setAudioModeAsync,
  useAudioPlayer,
  useAudioPlayerStatus,
} from 'expo-audio';

type RecordingPlayerProps = {
  uri: string;
};

export default function RecordingPlayer({ uri }: RecordingPlayerProps) {
  const player = useAudioPlayer(uri);
  const status = useAudioPlayerStatus(player);

  const [isBusy, setIsBusy] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const operationInProgress = useRef(false);

  async function handlePlayback() {
    if (operationInProgress.current || !player.isLoaded) {
      return;
    }

    operationInProgress.current = true;
    setIsBusy(true);
    setErrorMessage(null);

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

      setErrorMessage(
        'Không thể phát bản ghi. Hãy thử lại hoặc thu một đoạn mới.',
      );
    } finally {
      setIsBusy(false);
      operationInProgress.current = false;
    }
  }

  const disabled = isBusy || !status.isLoaded;

  return (
    <View style={styles.container}>
      <Text style={styles.status}>
        {status.isLoaded
          ? `${Math.floor(status.currentTime)} / ${Math.floor(status.duration)} giây`
          : 'Đang tải bản ghi...'}
      </Text>

      <Pressable
        accessibilityRole="button"
        accessibilityState={{ disabled }}
        disabled={disabled}
        onPress={handlePlayback}
        style={({ pressed }) => [
          styles.button,
          (pressed || disabled) && styles.dimmed,
        ]}
      >
        <Text style={styles.buttonText}>
          {isBusy
            ? 'Đang xử lý...'
            : status.playing
              ? 'Dừng phát'
              : 'Phát từ đầu'}
        </Text>
      </Pressable>

      {errorMessage !== null && (
        <Text accessibilityRole="alert" style={styles.error}>
          {errorMessage}
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: 12,
  },
  status: {
    color: '#CBD5E1',
    fontSize: 14,
  },
  button: {
    borderColor: '#5EEAD4',
    borderWidth: 1,
    borderRadius: 12,
    paddingVertical: 14,
    paddingHorizontal: 20,
    alignItems: 'center',
  },
  buttonText: {
    color: '#5EEAD4',
    fontSize: 16,
    fontWeight: '600',
  },
  dimmed: {
    opacity: 0.5,
  },
  error: {
    color: '#FCA5A5',
    fontSize: 14,
    lineHeight: 22,
  },
});