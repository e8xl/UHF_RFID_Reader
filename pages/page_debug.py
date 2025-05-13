from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                               QMessageBox)
from qfluentwidgets import LineEdit, PushButton, TextEdit


class DebugPage(QWidget):
    """调试页面类"""

    def __init__(self, main_window):
        """
        初始化调试页面
        参数:
            main_window: 主窗口实例
        """
        super().__init__()
        self.main_window = main_window
        self.setObjectName("debugPage")  # 添加对象名称
        self.setup_ui()

    def setup_ui(self):
        """设置界面布局"""
        layout = QVBoxLayout(self)
        # 设置布局的边距，增加顶部边距使内容下移
        layout.setContentsMargins(16, 48, 16, 16)  # 左、上、右、下的边距

        # 创建命令输入框
        self.command_input = LineEdit(self)
        self.command_input.setPlaceholderText("输入16进制命令，例如: BB 00 39 00 09 00 00 00 00 01 00 02 00 06 4B 7E")

        # 创建按钮布局
        button_layout = QHBoxLayout()
        self.btn_send = PushButton('发送命令', self)
        self.btn_clear = PushButton('清空日志', self)
        button_layout.addWidget(self.btn_send)
        button_layout.addWidget(self.btn_clear)
        button_layout.addStretch()

        # 创建日志显示框
        self.log_display = TextEdit(self)
        self.log_display.setReadOnly(True)

        # 添加所有控件到主布局
        layout.addWidget(self.command_input)
        layout.addLayout(button_layout)
        layout.addWidget(self.log_display)

        # 连接信号和槽
        self.btn_send.clicked.connect(self.send_command)
        self.btn_clear.clicked.connect(self.clear_log)

    def validate_command(self, command_str):
        """
        验证命令格式是否正确
        参数:
            command_str: 命令字符串
        返回:
            (bool, str): (是否有效, 错误信息)
        """
        # 移除所有空格
        command_str = command_str.replace(" ", "")

        # 检查长度是否为偶数
        if len(command_str) % 2 != 0:
            return False, "命令长度必须为偶数"

        # 检查是否都是有效的16进制字符
        try:
            bytes.fromhex(command_str)
        except ValueError:
            return False, "命令包含无效的16进制字符"

        # 检查命令格式
        command_bytes = bytes.fromhex(command_str)
        if len(command_bytes) < 7:  # 最小长度检查
            return False, "命令长度过短"

        # 检查帧头和帧尾
        if command_bytes[0] != 0xBB:
            return False, "无效的帧头（必须为BB）"
        if command_bytes[-1] != 0x7E:
            return False, "无效的帧尾（必须为7E）"

        # 检查校验和
        calculated_checksum = sum(command_bytes[1:-2]) & 0xFF
        received_checksum = command_bytes[-2]
        if calculated_checksum != received_checksum:
            return False, f"校验和错误（计算值：{calculated_checksum:02X}，接收值：{received_checksum:02X}）"

        return True, "命令格式正确"

    def send_command(self):
        """发送命令"""
        command_str = self.command_input.text().strip()
        if not command_str:
            QMessageBox.warning(self, "警告", "请输入命令")
            return

        # 验证命令格式
        is_valid, message = self.validate_command(command_str)
        if not is_valid:
            QMessageBox.warning(self, "命令格式错误", message)
            return

        # 转换命令为字节数组
        command_bytes = bytes.fromhex(command_str.replace(" ", ""))

        # 记录发送的命令
        self.append_log(f"发送命令: {' '.join([f'{b:02X}' for b in command_bytes])}")

        # 检查设备连接状态
        if not self.main_window.ser or not self.main_window.ser.is_open:
            self.append_log("错误: 设备未连接")
            return

        try:
            # 发送命令并获取响应
            response = self.main_window.send_command(command_bytes)
            if response:
                self.append_log(f"收到响应: {' '.join([f'{b:02X}' for b in response])}")
            else:
                self.append_log("未收到响应")
        except Exception as e:
            self.append_log(f"发送命令出错: {str(e)}")

    def append_log(self, message):
        """
        添加日志信息
        参数:
            message: 日志消息
        """
        self.log_display.append(message)

    def clear_log(self):
        """清空日志显示"""
        self.log_display.clear()
