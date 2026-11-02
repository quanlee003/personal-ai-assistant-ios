export type CommandResult =
  | {
      status: 'completed' | 'unsupported' | 'invalid';
      message: string;
    }
  | {
      status: 'requires_action';
      action: {
        type: 'create_note';
        content: string;
      };
    };

export function handleCommand(instruction: string): CommandResult {
  const cleanedInstruction = instruction.trim();
  const normalizedInstruction = cleanedInstruction.toLowerCase();
  const notePrefix = 'ghi chú:';

  if (normalizedInstruction.startsWith(notePrefix)) {
    const content = cleanedInstruction.slice(notePrefix.length).trim();

    if (content.length === 0) {
      return {
        status: 'invalid',
        message: 'Bạn cần nhập nội dung sau "ghi chú:".',
      };
    }

    return {
      status: 'requires_action',
      action: {
        type: 'create_note',
        content,
      },
    };
  }

  switch (normalizedInstruction) {
    case 'trợ giúp':
    case 'help':
      return {
        status: 'completed',
        message:
          'Các lệnh hiện có: "trợ giúp", "trạng thái" và ' +
          '"ghi chú: nội dung". Ghi chú chỉ được giữ trong phiên chạy.',
      };

    case 'trạng thái':
    case 'status':
      return {
        status: 'completed',
        message:
          'Bộ xử lý lệnh cục bộ đang hoạt động. ' +
          'Ghi chú chưa được lưu lâu dài. Chưa kết nối AI hoặc microphone.',
      };

    default:
      return {
        status: 'unsupported',
        message:
          'Yêu cầu này chưa được hỗ trợ. ' +
          'Nhập "trợ giúp" để xem các lệnh hiện có.',
      };
  }
}