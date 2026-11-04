import { useRef, useState } from 'react';
import {
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

type TranscriptEditorProps = {
  value: string;
  disabled: boolean;
  onSave: (text: string) => Promise<boolean>;
  onTextChange: (text: string) => void;
};

export default function TranscriptEditor({
  value,
  disabled,
  onSave,
  onTextChange,
}: TranscriptEditorProps) {
  const draft = value;

  const [isSaving, setIsSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const saveInProgress = useRef(false);

  const locked = disabled || isSaving;
  const canSave = !locked && !saved && draft.trim().length > 0;

  async function handleSave() {
    if (!canSave || saveInProgress.current) {
      return;
    }

    saveInProgress.current = true;
    setIsSaving(true);
    setError(null);

    try {
      const success = await onSave(draft.trim());

      if (success) {
        setSaved(true);
      } else {
        setError('Chưa lưu được. Nội dung được giữ lại để thử lại.');
      }
    } catch (error: unknown) {
      console.error('Lỗi lưu transcript:', error);
      setError('Chưa xác nhận lưu thành công. Hãy kiểm tra và thử lại.');
    } finally {
      setIsSaving(false);
      saveInProgress.current = false;
    }
  }

  return (
    <View style={styles.container}>
      <Text style={styles.label}>Kiểm tra và chỉnh sửa văn bản</Text>

      <TextInput
        accessibilityLabel="Chỉnh sửa văn bản nhận dạng"
        style={styles.input}
        value={draft}
        onChangeText={(text) => {
            setSaved(false);
            setError(null);
            onTextChange(text);
        }}
        multiline
        textAlignVertical="top"
        editable={!locked}
        placeholder="Nội dung ghi chú"
        placeholderTextColor="#94A3B8"
      />

      <Pressable
        accessibilityRole="button"
        accessibilityState={{
          disabled: !canSave,
          busy: isSaving,
        }}
        disabled={!canSave}
        onPress={handleSave}
        style={({ pressed }) => [
          styles.button,
          (!canSave || pressed) && styles.dimmed,
        ]}
      >
        <Text style={styles.buttonText}>
          {isSaving
            ? 'Đang lưu...'
            : saved
              ? 'Đã lưu ghi chú'
              : 'Lưu ghi chú'}
        </Text>
      </Pressable>

      {saved && (
        <Text accessibilityLiveRegion="polite" style={styles.success}>
          Đã lưu trên thiết bị. Nếu sửa tiếp rồi lưu, một ghi chú mới
          sẽ được tạo.
        </Text>
      )}

      {error !== null && (
        <Text accessibilityRole="alert" style={styles.error}>
          {error}
        </Text>
      )}

      <Text style={styles.note}>
        Văn bản được tự lưu riêng dưới dạng bản nháp trên thiết bị.
        Hãy kiểm tra trạng thái lưu trước khi đóng app. Audio không
        được khôi phục cùng bản nháp.
       </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#0F172A',
    borderRadius: 12,
    padding: 16,
    gap: 12,
  },
  label: {
    color: '#CBD5E1',
    fontSize: 14,
  },
  input: {
    minHeight: 140,
    maxHeight: 300,
    borderWidth: 1,
    borderColor: '#475569',
    borderRadius: 10,
    padding: 12,
    color: '#F8FAFC',
    fontSize: 16,
    lineHeight: 26,
  },
  button: {
    backgroundColor: '#5EEAD4',
    borderRadius: 12,
    padding: 14,
    alignItems: 'center',
  },
  buttonText: {
    color: '#0B1120',
    fontSize: 16,
    fontWeight: '700',
  },
  dimmed: {
    opacity: 0.5,
  },
  success: {
    color: '#5EEAD4',
    fontSize: 14,
    lineHeight: 22,
  },
  error: {
    color: '#FCA5A5',
    fontSize: 14,
    lineHeight: 22,
  },
  note: {
    color: '#94A3B8',
    fontSize: 12,
    lineHeight: 18,
  },
});