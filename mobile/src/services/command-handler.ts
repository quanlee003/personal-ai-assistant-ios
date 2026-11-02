export type CommandResult = {
  status: 'completed' | 'unsupported';
  message: string;
};

export function handleCommand(instruction: string): CommandResult {
  const normalizedInstruction = instruction.trim().toLowerCase();

  switch (normalizedInstruction) {
    case 'trợ giúp':
    case 'help':
      return {
        status: 'completed',
        message:
          'Hiện tại tôi hỗ trợ hai lệnh: "trợ giúp" và "trạng thái". ' +
          'Tôi chưa thể mở hoặc điều khiển ứng dụng khác.',
      };

    case 'trạng thái':
    case 'status':
      return {
        status: 'completed',
        message:
          'Bộ xử lý lệnh cục bộ đang hoạt động. ' +
          'Chưa kết nối AI, microphone hoặc dịch vụ bên ngoài.',
      };

    default:
      return {
        status: 'unsupported',
        message:
          'Yêu cầu này chưa được hỗ trợ. ' +
          'Bạn có thể nhập "trợ giúp" để xem các lệnh hiện có.',
      };
  }
}