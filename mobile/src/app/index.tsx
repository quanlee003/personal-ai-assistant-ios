import { useRef, useState } from 'react';
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

type Note = {
  id: string;
  content: string;
};
export default function HomeScreen() {
  const [instruction, setInstruction] = useState('');
  const [lastInstruction, setLastInstruction] = useState('');
  const [commandResult, setCommandResult] = useState<CommandResult | null>(null);
  const [notes, setNotes] = useState<Note[]>([]);
  const nextNoteId = useRef(1);

  const canSend = instruction.trim().length > 0;

  function handleSend() {
    const cleanedInstruction = instruction.trim();

    if (cleanedInstruction.length === 0) {
      return;
    }

    const result = handleCommand(cleanedInstruction);

    if (result.status === 'requires_action') {
      const newNote: Note = {
        id: `note-${nextNoteId.current}`,
        content: result.action.content,
      };

      nextNoteId.current += 1;

      setNotes((previousNotes) => [newNote, ...previousNotes]);

      setCommandResult({
        status: 'completed',
        message: 'Đã thêm ghi chú vào danh sách của phiên hiện tại.',
      });
    } else {
      setCommandResult(result);
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
              {commandResult !== null &&
                commandResult.status !== 'requires_action' && (
                  <View style={styles.card}>
                    <Text style={styles.cardTitle}>Kết quả xử lý</Text>

                    <Text style={styles.note}>
                      {commandResult.status === 'completed'
                        ? 'Trạng thái: Đã xử lý'
                        : commandResult.status === 'invalid'
                          ? 'Trạng thái: Yêu cầu chưa hợp lệ'
                          : 'Trạng thái: Chưa hỗ trợ'}
                    </Text>

                    <Text style={styles.result}>
                      {commandResult.message}
                    </Text>
                  </View>
                )}
            <View style={styles.card}>
              <Text style={styles.cardTitle}>
                Ghi chú trong phiên ({notes.length})
              </Text>

              {notes.length === 0 ? (
                <Text style={styles.note}>Chưa có ghi chú nào.</Text>
              ) : (
                notes.map((note) => (
                  <View key={note.id} style={styles.noteItem}>
                    <Text style={styles.result}>{note.content}</Text>
                  </View>
                ))
              )}
            </View>
            <Text style={styles.result}>
              {lastInstruction || 'Bạn chưa gửi yêu cầu nào.'}
            </Text>
          </View>

          <Text style={styles.note}>
            Bản thử nghiệm xử lý lệnh theo quy tắc trên thiết bị.
            Chưa kết nối AI hoặc điều khiển ứng dụng khác.
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

  noteItem: {
    borderTopWidth: 1,
    borderTopColor: '#475569',
    paddingTop: 12,
  },
});