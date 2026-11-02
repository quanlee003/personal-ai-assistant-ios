import { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

export default function HomeScreen() {
  const [testCount, setTestCount] = useState(0);

  return (
    <View style={styles.container}>
      <View style={styles.content}>
        <Text style={styles.label}>PERSONAL AI ASSISTANT</Text>

        <Text style={styles.title}>Yo Quan!</Text>

        <Text style={styles.description}>
          Đây là điểm khởi đầu cho trợ lý cá nhân của bạn.
        </Text>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Trạng thái ứng dụng</Text>

          <Text style={styles.status}>
            {testCount === 0
              ? 'Sẵn sàng kiểm tra giao diện.'
              : `Đã nhận ${testCount} lần bấm thành công.`}
          </Text>

          <Text style={styles.note}>
            Bản thử nghiệm giao diện — chưa kết nối AI hoặc microphone.
          </Text>
        </View>

        <Pressable
          accessibilityRole="button"
          onPress={() => setTestCount((count) => count + 1)}
          style={({ pressed }) => [
            styles.button,
            pressed && styles.buttonPressed,
          ]}
        >
          <Text style={styles.buttonText}>Kiểm tra tương tác</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0B1120',
    paddingHorizontal: 24,
    paddingVertical: 32,
    justifyContent: 'center',
  },
  content: {
    width: '100%',
    maxWidth: 520,
    alignSelf: 'center',
    gap: 20,
  },
  label: {
    color: '#94A3B8',
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 2,
  },
  title: {
    color: '#F8FAFC',
    fontSize: 32,
    fontWeight: '700',
  },
  description: {
    color: '#CBD5E1',
    fontSize: 16,
    lineHeight: 24,
  },
  card: {
    backgroundColor: '#1E293B',
    borderRadius: 20,
    padding: 24,
    gap: 12,
  },
  cardTitle: {
    color: '#F8FAFC',
    fontSize: 18,
    fontWeight: '600',
  },
  status: {
    color: '#5EEAD4',
    fontSize: 16,
    lineHeight: 24,
  },
  note: {
    color: '#94A3B8',
    fontSize: 13,
    lineHeight: 20,
  },
  button: {
    backgroundColor: '#5EEAD4',
    paddingVertical: 16,
    paddingHorizontal: 20,
    borderRadius: 14,
    alignItems: 'center',
  },
  buttonPressed: {
    opacity: 0.75,
  },
  buttonText: {
    color: '#0B1120',
    fontSize: 16,
    fontWeight: '700',
  },
});