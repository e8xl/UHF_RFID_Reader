from typing import Optional, Any

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QApplication
from qfluentwidgets import SubtitleLabel, PushButton, LineEdit, TextEdit


class MainWindow(QWidget):
    """主窗口类型提示"""
    select_param: str
    ser: Any

    def send_command(self, command: bytearray) -> Optional[bytearray]: ...


class WritePage(QWidget):
    """
    写入功能页面类
    提供RFID标签数据写入功能的界面实现
    """

    def __init__(self, parent: Optional[QWidget] = None):
        """
        初始化写入页面
        参数:
            parent: 父窗口对象
        """
        super().__init__(parent=parent)
        # 设置页面标识
        self.setObjectName("writePage")

        # 初始化控件变量
        self.write_input = None  # 写入数据输入框
        self.btn_write = None  # 写入按钮
        self.write_page_log = None  # 日志显示区域

        # 新增读取EPC区域相关控件
        self.access_password_input = None  # 访问密码输入框
        self.start_addr_input = None  # 起始地址输入框
        self.length_input = None  # 读取长度输入框
        self.btn_read_epc = None  # 读取EPC按钮
        self.epc_result_text = None  # EPC读取结果显示

        # 初始化界面
        self.setup_ui()

    def setup_ui(self):
        """
        初始化用户界面
        设置布局和控件
        """
        # 创建主布局
        write_layout = QVBoxLayout(self)
        write_layout.setContentsMargins(20, 40, 20, 20)

        # 创建读取EPC功能组
        read_epc_group = QGroupBox("读取SELECT标签EPC", self)
        read_epc_layout = QHBoxLayout()
        read_epc_layout.setContentsMargins(10, 10, 10, 10)
        read_epc_layout.setSpacing(10)

        # 创建参数输入区域
        param_layout = QHBoxLayout()
        param_layout.setSpacing(5)

        # 访问密码输入
        param_layout.addWidget(QLabel("访问密码:"))
        self.access_password_input = LineEdit(self)
        self.access_password_input.setPlaceholderText("默认00000000")
        self.access_password_input.setText("00000000")
        self.access_password_input.setMaximumWidth(100)
        param_layout.addWidget(self.access_password_input)

        # 起始地址输入
        param_layout.addWidget(QLabel("起始地址:"))
        self.start_addr_input = LineEdit(self)
        self.start_addr_input.setPlaceholderText("默认2")
        self.start_addr_input.setText("2")
        self.start_addr_input.setMaximumWidth(60)
        param_layout.addWidget(self.start_addr_input)

        # 读取长度输入
        param_layout.addWidget(QLabel("读取长度:"))
        self.length_input = LineEdit(self)
        self.length_input.setPlaceholderText("默认6")
        self.length_input.setText("6")
        self.length_input.setMaximumWidth(60)
        param_layout.addWidget(self.length_input)

        # 读取按钮
        self.btn_read_epc = PushButton("读取EPC", self)
        self.btn_read_epc.clicked.connect(self.on_read_epc_clicked)
        self.btn_read_epc.setMaximumWidth(80)
        param_layout.addWidget(self.btn_read_epc)

        # 添加弹性空间
        param_layout.addStretch()

        # 将参数布局添加到主布局
        read_epc_layout.addLayout(param_layout)

        # EPC读取结果显示
        self.epc_result_text = TextEdit(self)
        self.epc_result_text.setReadOnly(True)
        self.epc_result_text.setPlaceholderText("EPC读取结果将显示在这里")
        self.epc_result_text.setMaximumHeight(60)
        read_epc_layout.addWidget(self.epc_result_text)

        read_epc_group.setLayout(read_epc_layout)
        write_layout.addWidget(read_epc_group)

        # 创建写入功能组
        write_group = QGroupBox("数据写入", self)
        write_group_layout = QVBoxLayout()
        write_group_layout.setContentsMargins(10, 20, 10, 10)
        write_group_layout.setSpacing(10)

        # 添加写入说明标签
        write_label = SubtitleLabel("请输入要写入的数字（最多12位数字）", self)
        write_group_layout.addWidget(write_label)

        # 创建输入区域布局
        input_layout = QHBoxLayout()
        input_layout.setSpacing(10)

        # 创建写入数据输入框
        self.write_input = LineEdit(self)
        self.write_input.setPlaceholderText("请输入数字（如：12345678）")
        self.write_input.setClearButtonEnabled(True)
        input_layout.addWidget(self.write_input)

        # 创建写入按钮
        self.btn_write = PushButton("写入数据", self)
        self.btn_write.setMinimumHeight(30)
        input_layout.addWidget(self.btn_write)

        # 将输入布局添加到写入功能组
        write_group_layout.addLayout(input_layout)
        write_group.setLayout(write_group_layout)
        write_layout.addWidget(write_group)

        # 创建日志显示区域
        log_group = QGroupBox("日志", self)
        log_layout = QVBoxLayout()
        log_layout.setContentsMargins(5, 5, 5, 5)

        # 添加清空日志按钮
        btn_clear_log = PushButton("清空日志", self)
        btn_clear_log.clicked.connect(self.clear_log)
        log_layout.addWidget(btn_clear_log)

        # 创建日志文本框
        self.write_page_log = TextEdit(self)
        self.write_page_log.setReadOnly(True)
        log_layout.addWidget(self.write_page_log)
        log_group.setLayout(log_layout)
        write_layout.addWidget(log_group)

        # 设置主布局
        self.setLayout(write_layout)

        # 在写入按钮初始化后添加点击事件连接
        self.btn_write.clicked.connect(self.on_write_clicked)

        # 在所有控件初始化完成后检查SELECT状态
        self.check_select_status()

    @staticmethod
    def get_main_window() -> Optional[MainWindow]:
        """
        获取主窗口引用的辅助方法
        返回:
            MainWindow对象或None
        """
        window = QApplication.activeWindow()
        return window if isinstance(window, MainWindow) else None

    def read_select_epc(self):
        """
        读取SELECT标签的EPC区域
        返回:
            生成的命令字节数组
        """
        # 获取输入值
        access_pwd = self.access_password_input.text().strip()
        if not access_pwd:
            access_pwd = "00000000"  # 默认密码
        elif len(access_pwd) < 8:
            # 如果输入的密码不足8位，在前面补0
            access_pwd = access_pwd.zfill(8)

        # 获取并验证起始地址和长度
        try:
            start_addr = int(self.start_addr_input.text().strip())
            length = int(self.length_input.text().strip())

            # 验证范围
            if not (0 <= start_addr <= 255):
                self.append_log("错误：起始地址必须在0-255之间")
                return None
            if not (1 <= length <= 255):
                self.append_log("错误：读取长度必须在1-255之间")
                return None

        except ValueError:
            self.append_log("错误：起始地址和读取长度必须是有效的数字")
            return None

        # 构建命令
        command = bytearray([
            0xBB,  # 帧头
            0x00,  # Type
            0x39,  # Command
            0x00,  # PL(MSB)
            0x09,  # PL(LSB)
        ])

        # 添加访问密码（4字节）
        try:
            # 确保密码是有效的16进制字符串
            pwd_bytes = bytes.fromhex(access_pwd)
            if len(pwd_bytes) != 4:  # 4字节密码
                self.append_log(f"错误：访问密码必须是4字节（8位16进制数），当前长度：{len(pwd_bytes)}字节")
                return None
            command.extend(pwd_bytes)  # 添加4字节密码
        except ValueError as e:
            self.append_log(f"错误：访问密码格式无效，必须是有效的16进制数：{str(e)}")
            return None

        command.extend([
            0x01,  # MemBank (01=EPC)
            start_addr & 0xFF,  # 起始地址低字节
            (start_addr >> 8) & 0xFF,  # 起始地址高字节
            length & 0xFF,  # 长度低字节
            (length >> 8) & 0xFF  # 长度高字节
        ])

        # 计算校验和
        checksum = sum(command[1:]) & 0xFF
        command.append(checksum)
        command.append(0x7E)  # 帧尾

        return command

    def parse_read_response(self, response):
        """
        解析读取EPC的响应数据
        参数:
            response: 响应数据字节数组
        返回:
            解析后的EPC数据字符串
        """
        if not response or len(response) < 8:
            return "响应数据无效"

        # 检查响应类型
        response_type = response[2]  # 0x39=成功, 0xFF=错误
        data_length = response[4]  # PL(LSB)

        # 提取RSSI和PC值（如果存在）
        rssi_dbm = None
        pc = None
        if len(response) >= 8:
            rssi_raw = response[5]
            if rssi_raw > 127:  # 负数
                rssi_dbm = -(256 - rssi_raw)
            else:  # 正数
                rssi_dbm = -rssi_raw

            if len(response) >= 8:
                pc = f"{response[6]:02X} {response[7]:02X}"
                self.append_log(f"PC: {pc}")
                self.append_log(f"RSSI: {rssi_dbm} dBm")

        # 获取主窗口引用，检查是否有SELECT参数
        main_window = self.get_main_window()
        has_select = main_window and hasattr(main_window, 'select_param') and main_window.select_param

        # 如果没有设置SELECT参数，返回错误
        if not has_select:
            return "读取失败：未设置SELECT参数，请先设置SELECT参数"

        # 提取EPC数据（无论成功还是失败）
        epc_str = None
        if response_type == 0x39 and len(response) >= 20:  # 成功响应
            epc_data = response[8:20]
            epc_str = ' '.join([f"{b:02X}" for b in epc_data])

            # 验证是否与SELECT参数匹配
            if main_window.select_param.replace(" ", "") == epc_str.replace(" ", ""):
                self.append_log("读取成功")
                return f"读取成功（SELECT匹配） - EPC: {epc_str}"
            else:
                return "读取失败：请检查SELECT设置是否正确或标签状态是否正确"

        elif response_type == 0xFF:  # 错误响应
            if data_length == 0x01:  # 简单错误响应
                if response[5] == 0x09:
                    return "读取失败：标签无响应"
                return "读取失败：设备返回错误"
            elif data_length == 0x10 and len(response) >= 20:  # 包含标签数据的错误响应
                epc_data = response[9:21]
                epc_str = ' '.join([f"{b:02X}" for b in epc_data])

                # 验证是否与SELECT参数匹配
                if main_window.select_param.replace(" ", "") == epc_str.replace(" ", ""):
                    return f"读取成功（SELECT匹配） - EPC: {epc_str}"
                else:
                    return "读取失败：请检查SELECT设置是否正确或标签状态是否正确"

        return "响应格式无效"

    @Slot()
    def clear_log(self):
        """
        清空日志显示区域的内容
        """
        if self.write_page_log:
            self.write_page_log.clear()

    def append_log(self, message):
        """
        添加日志消息到显示区域
        参数:
            message: 要添加的日志消息
        """
        if self.write_page_log:
            self.write_page_log.append(message)

    @Slot()
    def on_read_epc_clicked(self):
        """
        处理读取EPC按钮点击事件
        """
        main_window = self.get_main_window()
        if not main_window:
            self.append_log("错误：无法访问主窗口")
            self.epc_result_text.setText("错误：无法访问主窗口")
            return

        if not hasattr(main_window, 'send_command'):
            self.append_log("错误：主窗口未实现send_command方法")
            self.epc_result_text.setText("错误：主窗口未实现send_command方法")
            return

        if not main_window.ser:
            self.append_log("错误：设备未连接")
            self.epc_result_text.setText("错误：设备未连接")
            return

        # 获取命令
        command = self.read_select_epc()
        if not command:
            return

        # 记录发送的命令
        self.append_log(f"发送命令: {' '.join([f'{b:02X}' for b in command])}")

        try:
            # 发送命令并获取响应
            response = main_window.send_command(command)

            if response:
                # 记录收到的响应
                self.append_log(f"收到响应: {' '.join([f'{b:02X}' for b in response])}")

                # 解析响应数据
                epc_data = self.parse_read_response(response)
                self.epc_result_text.setText(epc_data)

                if "失败" not in epc_data and "无效" not in epc_data:
                    self.append_log(f"读取成功，EPC数据: {epc_data}")
                else:
                    self.append_log(epc_data)
            else:
                self.append_log("未收到响应")
                self.epc_result_text.setText("读取失败：未收到响应")
        except Exception as e:
            self.append_log(f"读取过程出错: {str(e)}")
            self.epc_result_text.setText(f"读取出错: {str(e)}")

    def write_epc_data(self):
        """
        生成写入EPC数据的命令
        返回:
            生成的命令字节数组，如果输入无效则返回None
        """
        # 获取写入数据
        write_data = self.write_input.text().strip()

        # 验证输入是否为纯数字
        if not write_data.isdigit():
            self.append_log("错误：请输入纯数字")
            return None

        # 限制最大长度为12位数字
        if len(write_data) > 12:
            self.append_log("错误：最多只能输入12位数字")
            return None

        # 处理数字串，两位一组转换为字节值
        hex_pairs = []
        # 补齐到偶数位
        if len(write_data) % 2 != 0:
            write_data = write_data + '0'

        # 两位两位处理数字，直接作为十六进制值使用
        for i in range(0, len(write_data), 2):
            # 直接将两位数字作为十六进制值使用
            hex_str = write_data[i:i + 2]
            hex_pairs.append(int(hex_str, 16))

        # 补充剩余字节为0，确保总是12字节
        while len(hex_pairs) < 12:
            hex_pairs.append(0)

        # 构建命令
        command = bytearray([
            0xBB,  # 帧头
            0x00,  # Type
            0x49,  # Command (写入命令)
            0x00,  # PL(MSB)
            0x15,  # PL(LSB) - 21字节数据
            0x00, 0x00, 0x00, 0x00,  # 访问密码（默认）
            0x01,  # MemBank (01=EPC)
            0x00, 0x02,  # 起始地址
            0x00, 0x06  # 写入长度（6个字）
        ])

        # 添加写入数据
        command.extend(hex_pairs)

        # 计算校验和
        checksum = sum(command[1:]) & 0xFF
        command.append(checksum)
        command.append(0x7E)  # 帧尾

        # 记录实际写入的EPC数据
        epc_str = ' '.join([f"{b:02X}" for b in hex_pairs])
        self.append_log(f"实际写入的EPC数据: {epc_str}")

        return command

    def parse_write_response(self, response):
        """
        解析写入响应数据
        参数:
            response: 响应数据字节数组
        返回:
            解析结果字符串
        """
        if not response or len(response) < 8:
            return "响应数据无效"

        # 检查响应格式
        if response[2] == 0x49:  # 写入命令的响应
            if len(response) >= 20:  # 成功响应（包含EPC数据）
                epc_data = response[9:21]
                epc_str = ' '.join([f"{b:02X}" for b in epc_data])
                self.append_log(f"标签当前EPC: {epc_str}")
                return "写入成功"
            return "写入成功"  # 即使没有返回EPC数据也认为成功
        elif response[2] == 0xFF and response[4] == 0x01:
            return "写入失败：标签无响应"

        return "写入失败：响应格式无效"

    def check_select_status(self):
        """
        检查SELECT参数状态并更新UI
        """
        if not self.btn_write or not self.write_input:
            return

        main_window = self.get_main_window()
        # 确保has_select是布尔值
        has_select = bool(main_window and hasattr(main_window, 'select_param') and main_window.select_param)

        self.btn_write.setEnabled(has_select)
        if not has_select:
            self.btn_write.setToolTip("请先设置SELECT参数")
            self.write_input.setPlaceholderText("请先设置SELECT参数后再进行写入操作")
        else:
            self.btn_write.setToolTip("")
            self.write_input.setPlaceholderText("请输入写入数据 (16字节以内)")

        self.write_input.setEnabled(has_select)

    def showEvent(self, event):
        """
        页面显示时触发
        """
        super().showEvent(event)
        # 每次显示页面时检查SELECT状态
        self.check_select_status()

    @Slot()
    def on_write_clicked(self):
        """
        处理写入按钮点击事件
        """
        main_window = self.get_main_window()
        if not main_window:
            self.append_log("错误：无法访问主窗口")
            return

        if not hasattr(main_window, 'send_command'):
            self.append_log("错误：主窗口未实现send_command方法")
            return

        if not main_window.ser:
            self.append_log("错误：设备未连接")
            return

        # 再次检查SELECT参数（以防万一）
        if not hasattr(main_window, 'select_param') or not main_window.select_param:
            self.append_log("错误：未设置SELECT参数，请先设置SELECT参数")
            self.check_select_status()
            return

        # 获取写入命令
        command = self.write_epc_data()
        if not command:
            return

        # 记录发送的命令
        self.append_log(f"发送命令: {' '.join([f'{b:02X}' for b in command])}")

        try:
            # 发送命令并获取响应
            response = main_window.send_command(command)

            if response:
                # 记录收到的响应
                self.append_log(f"收到响应: {' '.join([f'{b:02X}' for b in response])}")

                # 解析响应数据
                result = self.parse_write_response(response)
                self.append_log(result)
            else:
                self.append_log("写入失败：未收到响应")
        except Exception as e:
            self.append_log(f"写入过程出错: {str(e)}")
