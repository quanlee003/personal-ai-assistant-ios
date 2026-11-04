import { Pressable, StyleSheet, Text, View } from 'react-native';

type RecordingPlayerProps = {
  isLoaded: boolean;
  isPlaying: boolean;
  isBusy: boolean;
  disabled: boolean;
  currentTime: number;
  duration: number;
  errorMessage: string | null;
  onTogglePlayback: () => Promise<void>;
};

export default function RecordingPlayer({
  isLoaded,
  isPlaying,
  isBusy,
  disabled,
  currentTime,
  duration,
  errorMessage,
  onTogglePlayback,
}: RecordingPlayerProps) {
  return (
    <View style={styles.container}>
      <Text style={styles.status}>
        {isLoaded
          ? `${Math.floor(currentTime)} / ${Math.floor(duration)} giây`
          : 'Đang tải bản ghi...'}
      </Text>

      <Pressable
        accessibilityRole="button"
        accessibilityState={{
          disabled,
          busy: isBusy,
        }}
        disabled={disabled}
        onPress={onTogglePlayback}
        style={({ pressed }) => [
          styles.button,
          (pressed || disabled) && styles.dimmed,
        ]}
      >
        <Text style={styles.buttonText}>
          {isBusy
            ? 'Đang xử lý...'
            : isPlaying
              ? 'Tạm dừng phát'
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