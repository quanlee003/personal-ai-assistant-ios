import { useState } from 'react';
import {
  Keyboard,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import {
  handleCommand,
  type CommandResult,
} from '../services/command-handler';

export default function HomeScreen() {
  const [instruction, setInstruction] = useState('');
  const [lastInstruction, setLastInstruction] = useState('');

  const canSend = instruction.trim().length > 0;

  function handleSend() {
    const cleanedInstruction = instruction.trim();

    if (cleanedInstruction.length === 0) {
      return;
    }

    setLastInstruction(cleanedInstruction);
    setInstruction('');
    Keyboard.dismiss();
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.content}>
          <Text style={styles.label}>PERSONAL AI ASSISTANT</Text>

          <Text style={styles.title}>Xin chào, Quan.</Text>

          <Text style={styles.description}>
            Bạn muốn trợ lý hỗ trợ điều gì?
          </Text>

          <View style={styles.card}>
            <Text style={styles.cardTitle}>Yêu cầu của bạn</Text>

            <TextInput
              accessibilityLabel="Nhập yêu cầu cho trợ lý"
              style={styles.input}
              placeholder="Ví dụ: Mở Spotify"
              placeholderTextColor="#94A3B8"
              value={instruction}
              onChangeText={setInstruction}
              maxLength={500}
              returnKeyType="send"
              onSubmitEditing={handleSend}
            />

            <Pressable
              accessibilityRole="button"
              accessibilityState={{ disabled: !canSend }}
              disabled={!canSend}
              onPress={handleSend}
              style={({ pressed }) => [
                styles.button,
                !canSend && styles.buttonDisabled,
                pressed && styles.buttonPressed,
              ]}
            >
              <Text style={styles.buttonText}>Gửi yêu cầu</Text>
            </Pressable>
          </View>

          <View style={styles.card}>
            <Text style={styles.cardTitle}>Yêu cầu vừa gửi</Text>

            <Text style={styles.result}>
              {lastInstruction || 'Bạn chưa gửi yêu cầu nào.'}
            </Text>
          </View>

          <Text style={styles.note}>
            Bản thử nghiệm chỉ hiển thị yêu cầu. Chưa kết nối AI,
            chưa thực hiện hành động và chưa lưu dữ liệu lâu dài.
          </Text>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0B1120',
  },
  scrollContent: {
    flexGrow: 1,
    justifyContent: 'center',
    paddingHorizontal: 24,
    paddingVertical: 32,
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
    padding: 20,
    gap: 16,
  },
  cardTitle: {
    color: '#F8FAFC',
    fontSize: 18,
    fontWeight: '600',
  },
  input: {
    backgroundColor: '#0F172A',
    color: '#F8FAFC',
    borderColor: '#475569',
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 14,
    fontSize: 16,
  },
  button: {
    backgroundColor: '#5EEAD4',
    paddingVertical: 16,
    paddingHorizontal: 20,
    borderRadius: 12,
    alignItems: 'center',
  },
  buttonDisabled: {
    opacity: 0.4,
  },
  buttonPressed: {
    opacity: 0.75,
  },
  buttonText: {
    color: '#0B1120',
    fontSize: 16,
    fontWeight: '700',
  },
  result: {
    color: '#5EEAD4',
    fontSize: 16,
    lineHeight: 24,
  },
  note: {
    color: '#94A3B8',
    fontSize: 13,
    lineHeight: 20,
  },
});