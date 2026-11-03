import { useRef, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { checkBackendHealth } from '../services/backend-api';

export default function BackendStatus() {
  const [isChecking, setIsChecking] = useState(false);
  const [message, setMessage] = useState('Chưa kiểm tra backend.');
  const [hasError, setHasError] = useState(false);

  const requestInProgress = useRef(false);

  async function handleCheck() {
    if (requestInProgress.current) {
      return;
    }

    requestInProgress.current = true;
    setIsChecking(true);
    setHasError(false);
    setMessage('Đang kết nối...');

    try {
      await checkBackendHealth();
      setMessage('Backend phản hồi: ok');
    } catch (error: unknown) {
      console.error('Kiểm tra backend thất bại:', error);

      setHasError(true);
      setMessage(
        'Không xác nhận được kết nối. Kiểm tra backend đang chạy, ' +
          'IP trong .env và mạng Wi-Fi. Request có thể đã hết thời gian chờ.',
      );
    } finally {
      requestInProgress.current = false;
      setIsChecking(false);
    }
  }

  return (
    <View style={styles.card}>
      <Text style={styles.title}>Kết nối backend</Text>

      <Text style={[styles.message, hasError && styles.error]}>
        {message}
      </Text>

      <Pressable
        accessibilityRole="button"
        accessibilityState={{ disabled: isChecking }}
        disabled={isChecking}
        onPress={handleCheck}
        style={({ pressed }) => [
          styles.button,
          (pressed || isChecking) && styles.dimmed,
        ]}
      >
        <Text style={styles.buttonText}>
          {isChecking ? 'Đang kiểm tra...' : 'Kiểm tra kết nối'}
        </Text>
      </Pressable>
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
  message: {
    color: '#5EEAD4',
    fontSize: 14,
    lineHeight: 22,
  },
  error: {
    color: '#FCA5A5',
  },
  button: {
    borderColor: '#5EEAD4',
    borderWidth: 1,
    borderRadius: 12,
    padding: 14,
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
});