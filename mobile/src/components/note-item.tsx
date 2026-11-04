import { useRef, useState } from 'react';
import {
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import type { Note } from '../types/note';

type NoteItemProps = {
  note: Note;
  disabled: boolean;
  onSave: (content: string) => Promise<boolean>;
  onDelete: () => Promise<boolean>;
};

export default function NoteItem({
  note,
  disabled,
  onSave,
  onDelete,
}: NoteItemProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState(note.content);
  const [isWorking, setIsWorking] = useState(false);

  const operationInProgress = useRef(false);

  const locked = disabled || isWorking;

  const canSave =
    !locked &&
    draft.trim().length > 0 &&
    draft.trim() !== note.content;

  function startEditing() {
    if (locked) {
      return;
    }

    setDraft(note.content);
    setIsEditing(true);
  }

  function cancelEditing() {
    if (locked) {
      return;
    }

    setDraft(note.content);
    setIsEditing(false);
  }

  async function handleSave() {
    if (!canSave || operationInProgress.current) {
      return;
    }

    operationInProgress.current = true;
    setIsWorking(true);

    try {
      const success = await onSave(draft.trim());

      if (success) {
        setIsEditing(false);
      }
    } catch (error: unknown) {
      console.error('Lỗi cập nhật ghi chú:', error);
    } finally {
      operationInProgress.current = false;
      setIsWorking(false);
    }
  }

  async function handleDelete() {
    if (locked || operationInProgress.current) {
      return;
    }

    operationInProgress.current = true;
    setIsWorking(true);

    try {
      await onDelete();
    } catch (error: unknown) {
      console.error('Lỗi xóa ghi chú:', error);
    } finally {
      operationInProgress.current = false;
      setIsWorking(false);
    }
  }

  return (
    <View style={styles.container}>
      {isEditing ? (
        <>
          <Text style={styles.label}>Chỉnh sửa ghi chú</Text>

          <TextInput
            accessibilityLabel="Nội dung ghi chú đang chỉnh sửa"
            style={styles.input}
            value={draft}
            onChangeText={setDraft}
            multiline
            textAlignVertical="top"
            editable={!locked}
          />

          <View style={styles.actions}>
            <Pressable
              accessibilityRole="button"
              accessibilityState={{ disabled: !canSave }}
              disabled={!canSave}
              onPress={handleSave}
              style={[styles.button, !canSave && styles.dimmed]}
            >
              <Text style={styles.buttonText}>
                {isWorking ? 'Đang xử lý...' : 'Lưu thay đổi'}
              </Text>
            </Pressable>

            <Pressable
              accessibilityRole="button"
              accessibilityState={{ disabled: locked }}
              disabled={locked}
              onPress={cancelEditing}
              style={[styles.button, locked && styles.dimmed]}
            >
              <Text style={styles.buttonText}>Hủy sửa</Text>
            </Pressable>
          </View>
        </>
      ) : (
        <>
          <Text selectable style={styles.content}>
            {note.content}
          </Text>

          <View style={styles.actions}>
            <Pressable
              accessibilityRole="button"
              accessibilityState={{ disabled: locked }}
              disabled={locked}
              onPress={startEditing}
              style={[styles.button, locked && styles.dimmed]}
            >
              <Text style={styles.buttonText}>Sửa</Text>
            </Pressable>

            <Pressable
              accessibilityRole="button"
              accessibilityState={{ disabled: locked }}
              disabled={locked}
              onPress={handleDelete}
              style={[styles.button, locked && styles.dimmed]}
            >
              <Text style={styles.deleteText}>
                {isWorking ? 'Đang xử lý...' : 'Xóa'}
              </Text>
            </Pressable>
          </View>
        </>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    borderTopWidth: 1,
    borderTopColor: '#475569',
    paddingTop: 16,
    gap: 12,
  },
  label: {
    color: '#CBD5E1',
    fontSize: 14,
  },
  content: {
    color: '#5EEAD4',
    fontSize: 16,
    lineHeight: 24,
  },
  input: {
    minHeight: 120,
    maxHeight: 300,
    backgroundColor: '#0F172A',
    color: '#F8FAFC',
    borderColor: '#475569',
    borderWidth: 1,
    borderRadius: 12,
    padding: 12,
    fontSize: 16,
    lineHeight: 24,
  },
  actions: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  button: {
    borderWidth: 1,
    borderColor: '#475569',
    borderRadius: 10,
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  buttonText: {
    color: '#5EEAD4',
    fontSize: 14,
    fontWeight: '600',
  },
  deleteText: {
    color: '#FCA5A5',
    fontSize: 14,
    fontWeight: '600',
  },
  dimmed: {
    opacity: 0.4,
  },
});