import { useEffect, useRef, useState } from 'react';
import type { Note } from '../types/note';
import { loadNotes, saveNotes } from '../services/note-storage';
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

import VoiceRecorder from '../components/voice-recorder';

export default function HomeScreen() {
  const [instruction, setInstruction] = useState('');
  const [lastInstruction, setLastInstruction] = useState('');
  const [commandResult, setCommandResult] = useState<CommandResult | null>(null);
  const [notes, setNotes] = useState<Note[]>([]);
  const [storageReady, setStorageReady] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [storageError, setStorageError] = useState<string | null>(null);

  const submissionInProgress = useRef(false);
  const nextNoteId = useRef(1);

  const canSend =
    storageReady &&
    !isSaving &&
    instruction.trim().length > 0;



  useEffect(() => {
    let ignore = false;

    async function restoreNotes() {
      try {
        const storedNotes = await loadNotes();

        if (ignore) {
          return;
        }

        setNotes(storedNotes);
        setStorageError(null);
        setStorageReady(true);
      } catch (error: unknown) {
        if (ignore) {
          return;
        }

        console.error('Không thể đọc ghi chú:', error);

        setStorageError(
          'Không thể đọc ghi chú đã lưu. Tính năng gửi đang bị khóa ' +
            'để tránh ghi đè dữ liệu. Hãy thử reload app.',
        );
      }
    }

    void restoreNotes();

    return () => {
      ignore = true;
    };
  }, []);



  async function handleSend() {
    const cleanedInstruction = instruction.trim();

    if (
      cleanedInstruction.length === 0 ||
      !storageReady ||
      submissionInProgress.current
    ) {
      return;
    }

    submissionInProgress.current = true;
    setStorageError(null);

    try {
      const result = handleCommand(cleanedInstruction);

      if (result.status === 'requires_action') {
        setIsSaving(true);

        let newNoteId = `note-${nextNoteId.current}`;

        while (notes.some((note) => note.id === newNoteId)) {
          nextNoteId.current += 1;
          newNoteId = `note-${nextNoteId.current}`;
        }

        const newNote: Note = {
          id: newNoteId,
          content: result.action.content,
        };

        nextNoteId.current += 1;

        const updatedNotes = [newNote, ...notes];

        await saveNotes(updatedNotes);

        setNotes(updatedNotes);

        setCommandResult({
          status: 'completed',
          message: 'Đã tạo và lưu ghi chú trên thiết bị.',
        });
      } else {
        setCommandResult(result);
      }

      setLastInstruction(cleanedInstruction);
      setInstruction('');
      Keyboard.dismiss();
    } catch (error: unknown) {
      console.error('Không thể xử lý yêu cầu:', error);

      setCommandResult(null);

      setStorageError(
        'Không thể hoàn tất lưu ghi chú. Chưa xác nhận thành công; ' +
          'nội dung nhập được giữ lại để bạn kiểm tra hoặc thử lại.',
      );
    } finally {
      setIsSaving(false);
      submissionInProgress.current = false;
    }
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

          <VoiceRecorder />

          {!storageReady && storageError === null && (
            <Text style={styles.note}>Đang đọc ghi chú đã lưu...</Text>
          )}

          {storageError !== null && (
            <Text accessibilityRole="alert" style={styles.error}>
              {storageError}
            </Text>
          )}

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
              editable={storageReady && !isSaving}
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
              <Text style={styles.buttonText}>
                {isSaving ? 'Đang lưu...' : 'Gửi yêu cầu'}
              </Text>
              
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
                Ghi chú trên thiết bị ({notes.length})
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
            Ghi chú được lưu cục bộ trên thiết bị, không được mã hóa
            và chưa đồng bộ cloud. Không nhập thông tin nhạy cảm.
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
  error: {
    color: '#FCA5A5',
    fontSize: 14,
    lineHeight: 22,
  },
});