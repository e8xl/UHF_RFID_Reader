#!/home/rfid/miniconda3/envs/rfid python
# -*- coding: utf-8 -*-
"""
Project Name: RFID Asset Management System
Version: V1.1.0
Created Date: 2025/02
Author: *

Description:
    基于PySide6开发的RFID资产管理系统GUI程序
    用于实现RFID标签的读取、写入及资产管理功能

Pages:
    - main（主界面）：用于连接设备和进行读卡器基础操作
    - write（写入界面）：用于给标签更改EPC卡号（暂未完成）
    - search（搜索界面）：搜索附近卡号是否有和数据库内asset值相匹配的数值
    - asset（群体搜索历史）：记录群体搜索的匹配日期、搜索设备名称，用于资产管理
    - match（匹配界面）：设定固定EPC卡号，找寻周围卡号，卡号是否有和数据库asset对应数据
    - blank（设置功率）：调整读写器功率设置
    - debug（调试页面）：用于调试和测试功能

Features:
    基础功能:
    - 串口设备的自动扫描与智能连接管理
    - 实时显示读取结果和详细操作日志
    - 读写器功率和增益的动态调节与显示
    - 支持断线自动重连和异常处理机制

    RFID操作:
    - RFID标签的单次读取和连续群读功能
    - 支持EPC数据的写入和验证
    - Select模式支持(可选择性读取特定EPC标签)
    - 支持多种Select操作模式(全局/部分/禁用)
    - Select参数的设置、验证和清除功能

    资产管理:
    - 群体搜索功能(支持批量搜索和匹配标签)
    - 实时卡号匹配与验证系统
    - 资产搜索功能(支持与数据库内资产信息实时匹配)
    - 搜索历史记录管理(记录搜索时间、设备和匹配结果)
    - 资产管理报表(支持搜索历史的统计和导出)

    用户界面:
    - 基于PySide6的现代化GUI界面
    - 多页面分层管理(主页/写入/搜索/资产/匹配/设置/调试)
    - 实时状态显示和反馈系统
    - 智能的错误提示和处理机制
    - 支持界面自适应不同屏幕分辨率

Tech Stack:
    - Python 3.8+
    - PySide6
    - pyserial
    - QFluentWidgets
    - SQLite3

Usage:
    直接运行本文件即可启动程序:
    python RFID_AssetManager.py

License:
    MIT License
"""
import sys
import time

import serial
from PySide6.QtCore import QTimer, QDateTime, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from qfluentwidgets import FluentTranslator
from qfluentwidgets import SplitFluentWindow, FluentIcon

from pages.page_asset import AssetPage
from pages.page_blank import BlankPage
from pages.page_debug import DebugPage
from pages.page_main import MainPage
from pages.page_match import MatchPage
from pages.page_search import SearchPage
from pages.page_write import WritePage
from serial_handler import (
    list_com_ports, connect_to_device, send_command,
    POWER_COMMANDS, SUCCESS_RESPONSE, SerialReadThread
)


class MainWindow(SplitFluentWindow):
    """
    主窗口类
    实现了RFID资产管理系统的主要功能和界面
    """

    def __init__(self):
        """
        初始化主窗口
        设置窗口属性、初始化成员变量、创建界面
        """
        super().__init__()
        # 设置窗口基本属性
        self.setWindowIcon(QIcon("icon.ico"))
        self.setWindowTitle("RFID_AssetManager V1.1")

        # 获取屏幕尺寸并设置窗口大小限制
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()  # 获取可用屏幕区域（排除任务栏）
            screen_width = screen_geometry.width()
            screen_height = screen_geometry.height()

            # 设置窗口的最小和最大尺寸
            self.setMinimumSize(800, 500)  # 最小尺寸
            self.setMaximumSize(screen_width, screen_height)  # 最大不超过可用屏幕区域

            # 设置初始窗口大小（根据屏幕尺寸动态调整）
            init_width = min(1024, int(screen_width * 0.9))  # 初始宽度为屏幕宽度的90%，但不超过1024
            init_height = min(600, int(screen_height * 0.9))  # 初始高度为屏幕高度的90%，但不超过600
            self.resize(init_width, init_height)

            # 将窗口移动到屏幕中央
            self.move(
                (screen_width - self.width()) // 2,
                (screen_height - self.height()) // 2
            )
        else:
            # 如果无法获取屏幕信息，使用默认尺寸
            self.resize(1024, 600)

        # 设置窗口标志，确保窗口不会超出屏幕边界
        self.setWindowFlags(
            self.windowFlags() | Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.WindowMinMaxButtonsHint)

        self.setStyleSheet("")

        # 设置导航面板宽度
        self.navigationInterface.setExpandWidth(200)

        # 初始化成员变量
        self.ser = None  # 串口对象
        self.log_count = 0  # 日志计数器
        self.current_power = None  # 当前功率值
        self.gain = None  # 当前增益值
        self.read_thread = None  # 读卡线程
        self.group_read_active = False  # 群读状态标志
        self.read_failed_logged = False  # 读取失败日志标志
        self.match_found = False  # 是否找到匹配标志

        # 添加Select模式相关变量
        self.select_mode = 0x01  # 默认不使用Select
        self.select_param = None  # Select参数

        # 初始化匹配提示定时器
        self.match_timer = QTimer(self)
        self.match_timer.timeout.connect(self.show_matching_status)
        self.match_timer.setInterval(1000)  # 设置1秒间隔

        # 创建并初始化各功能页面
        self.main_page = MainPage(self)
        self.write_page = WritePage(self)
        self.asset_page = AssetPage(self)
        self.blank_page = BlankPage(self)
        self.match_page = MatchPage(self)
        self.search_page = SearchPage(self)  # 创建新的搜索页面
        self.debug_page = DebugPage(self)  # 创建调试页面

        # 添加子界面到主窗口
        self.addSubInterface(self.main_page, FluentIcon.HOME, '主界面')
        self.addSubInterface(self.write_page, FluentIcon.EDIT, '写入功能')
        self.addSubInterface(self.search_page, FluentIcon.SEARCH, '群体搜索')
        self.addSubInterface(self.asset_page, FluentIcon.HISTORY, '群体搜索历史')
        self.addSubInterface(self.match_page, FluentIcon.ADD_TO, '卡号匹配')
        self.addSubInterface(self.blank_page, FluentIcon.SETTING, '功率设置')
        self.addSubInterface(self.debug_page, FluentIcon.SPEED_MEDIUM, '调试')  # 添加调试页面

        # 初始化匹配相关变量
        self.target_number = None  # 要匹配的目标数字
        self.matching_active = False  # 匹配状态标志

        # 连接信号和槽
        self.connect_signals()

    def connect_signals(self):
        """
        连接所有信号和槽函数
        建立用户界面事件与处理函数的关联
        """
        # 主页面按钮信号连接
        self.main_page.btn_clear_log.clicked.connect(self.clear_log)
        self.main_page.btn_scan_ports.clicked.connect(self.scan_ports)
        self.main_page.btn_connect_disconnect.clicked.connect(self.toggle_connection)
        self.main_page.btn_read_once.clicked.connect(self.read_card_once)
        self.main_page.btn_start_read.clicked.connect(self.read_cards)
        self.main_page.btn_stop_read.clicked.connect(self.stop_reading)
        self.main_page.btn_get_gain.clicked.connect(self.get_current_gain)
        self.main_page.btn_exit.clicked.connect(self.close)

        # Select功能信号连接
        self.main_page.combo_select_mode.currentIndexChanged.connect(self.on_select_mode_changed)
        self.main_page.btn_set_select.clicked.connect(self.on_set_select_clicked)
        self.main_page.btn_clear_select.clicked.connect(self.on_clear_select_clicked)
        self.main_page.btn_get_select.clicked.connect(self.get_select_params)

        # 写入页面按钮信号连接
        self.write_page.btn_write.clicked.connect(self.write_card)

        # 功率设置页面按钮信号连接
        self.blank_page.btn_set_power.clicked.connect(self.set_power)

    def log_message(self, message):
        """
        记录日志消息
        参数:
            message: 要记录的日志消息
        """
        self.log_count += 1
        timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss")
        log_entry = f"[{timestamp}] Set.{self.log_count}: {message}"

        # 更新主页面和写入页面的日志
        self.main_page.append_log(log_entry)
        self.write_page.append_log(log_entry)

    def scan_ports(self):
        """
        扫描并更新可用的COM端口列表
        """
        self.main_page.combo_ports.clear()
        ports = list_com_ports()
        if ports:
            for port, desc in ports:
                self.main_page.combo_ports.addItem(f"{port} ({desc})")
            self.main_page.btn_connect_disconnect.setEnabled(True)
            self.log_message(f"发现 {len(ports)} 个COM端口")
        else:
            self.log_message("未检测到任何COM端口")
            self.main_page.btn_connect_disconnect.setEnabled(False)

    def toggle_connection(self):
        """
        切换设备连接状态
        在连接和断开状态间切换
        """
        if self.ser:
            self.disconnect_device()
        else:
            self.connect_device()

    def connect_device(self):
        """
        连接到选定的串口设备
        """
        selected_port = self.main_page.combo_ports.currentText().split()[0]

        # 重新扫描COM口进行预检查
        available_ports = list_com_ports()
        available_port_names = [port[0] for port in available_ports]

        # 检查选择的端口是否仍然可用
        if selected_port not in available_port_names:
            self.log_message(f"错误: 未识别到串口设备 {selected_port}，请重新扫描")
            # 清空并更新端口列表
            self.main_page.combo_ports.clear()
            self.main_page.btn_connect_disconnect.setEnabled(False)
            return

        self.ser = connect_to_device(selected_port)
        if self.ser:
            # 更新界面状态为已连接
            self.main_page.label_status.setText(f"状态: 已连接到 {selected_port} 😊")
            self.main_page.label_status.setStyleSheet("""
                QLabel {
                    font-size: 16px;
                    font-weight: bold;
                    color: #1a8f1a;
                    padding: 0px;
                    margin: 0px;
                }
            """)
            self.main_page.btn_connect_disconnect.setText("断开设备")
            self.main_page.btn_connect_disconnect.setStyleSheet("""
                QPushButton {
                    background-color: #ccffcc;
                    border: none;
                    border-radius: 4px;
                    padding: 4px;
                }
                QPushButton:hover {
                    background-color: #99ff99;
                }
            """)
            self.log_message(f"成功连接到 {selected_port}")
            # 连接成功后获取当前增益
            self.get_current_gain()
        else:
            self.log_message(f"错误: {selected_port} 连接失败，请检查设备是否被其他程序占用")

    def disconnect_device(self):
        """
        断开当前连接的设备
        清理相关资源并更新界面状态
        """
        if self.ser:
            # 如果正在群读,先停止群读
            if self.group_read_active:
                try:
                    # 先发送停止群读命令
                    command = bytearray([0xBB, 0x00, 0x28, 0x00, 0x00, 0x28, 0x7E])
                    self.ser.write(command)
                    self.log_message("结束群读命令已发送")

                    # 等待群读完全停止
                    max_wait = 3  # 最大等待3秒
                    start_time = time.time()

                    while self.group_read_active and (time.time() - start_time) < max_wait:
                        time.sleep(0.1)  # 等待群读结束
                        QApplication.processEvents()  # 保持GUI响应

                    # 停止读卡线程
                    if self.read_thread:
                        self.read_thread.stop()
                        self.read_thread.wait()
                        self.read_thread = None

                    self.group_read_active = False
                    self.main_page.btn_start_read.setEnabled(True)
                    self.main_page.btn_stop_read.setEnabled(False)
                    self.log_message("群读已结束")

                except Exception as e:
                    self.log_message(f"停止群读时出错: {str(e)}")

            # 关闭串口连接
            if self.ser:
                try:
                    self.ser.close()
                except (serial.SerialException, IOError) as e:
                    self.log_message(f"关闭串口时出现错误: {str(e)}")
                self.ser = None

            # 更新界面状态
            self.main_page.label_status.setText("状态: 设备已断开 ⚠️")
            self.main_page.label_status.setStyleSheet("""
                QLabel {
                    font-size: 16px;
                    font-weight: bold;
                    color: #FF6B6B;
                    padding: 0px;
                    margin: 0px;
                }
            """)
            self.main_page.btn_connect_disconnect.setText("连接设备")
            self.main_page.btn_connect_disconnect.setStyleSheet("""
                QPushButton {
                    background-color: #ffcccc;
                    border: none;
                    border-radius: 4px;
                    padding: 4px;
                }
                QPushButton:hover {
                    background-color: #ff9999;
                }
            """)
            # 更新功率设置页面的标签
            self.blank_page.label_power.setText("当前功率/增益: --")
            self.log_message("设备已断开连接")
        else:
            self.log_message("设备未连接，无需断开")

    def set_power(self):
        """
        设置RFID读写器的发射功率
        """
        if not self.ser or not self.ser.is_open:
            self.log_message("设备未连接，无法设置功率")
            return

        selected_power = self.blank_page.combo_power.currentText()
        command = POWER_COMMANDS[selected_power]
        try:
            response = send_command(self.ser, command)
            if response == SUCCESS_RESPONSE:
                self.log_message(f"发射功率设置命令已发送: {selected_power}")
                # 设置成功后重新获取实际功率值
                self.get_current_gain()
            else:
                self.log_message(
                    f"发射功率设置失败: {response.hex().upper() if isinstance(response, bytes) else response}")
        except Exception as e:
            self.handle_serial_error(str(e))

    def read_card_once(self):
        """
        执行单次读卡操作
        """
        if not self.ser or not self.ser.is_open:
            self.log_message("设备未连接，无法读取卡号")
            return

        command = bytearray([0xBB, 0x00, 0x22, 0x00, 0x00, 0x22, 0x7E])
        try:
            response = send_command(self.ser, command)
            if response.startswith(bytearray([0xBB, 0x02, 0x22])):
                # 解析RSSI（有符号数转换）
                rssi_raw = response[5]
                if rssi_raw > 127:  # 负数
                    rssi_dbm = -(256 - rssi_raw)
                else:  # 正数
                    rssi_dbm = -rssi_raw

                # PC值（2字节，带空格分隔）
                pc = f"{response[6]:02X} {response[7]:02X}"

                # EPC值（12字节）
                epc_bytes = response[8:20]
                epc = ' '.join([f"{b:02X}" for b in epc_bytes])

                # CRC值（2字节，带空格分隔）
                crc = f"{response[20]:02X} {response[21]:02X}"

                # 创建包含所有信息的字典
                card_info = {
                    'rssi': f"{rssi_dbm}",  # 转换为dBm的字符串
                    'pc': pc,
                    'epc': epc,
                    'crc': crc
                }

                self.log_message(f"单次读取成功 - PC: {pc}, EPC: {epc}, CRC: {crc}, RSSI: {rssi_dbm} dBm")
                self.main_page.add_card_to_table(card_info)
            else:
                self.log_message("单次读取失败")
        except Exception as e:
            self.handle_serial_error(str(e))

    def read_cards(self):
        """
        启动群读模式
        持续读取多张卡片的信息
        """
        if not self.ser or not self.ser.is_open:
            self.log_message("设备未连接，无法进行群读")
            return

        if self.read_thread and self.read_thread.isRunning():
            self.log_message("群读已经在进行中")
            return

        command = bytearray([0xBB, 0x00, 0x27, 0x00, 0x03, 0x22, 0xFF, 0xFF, 0x4A, 0x7E])
        try:
            send_command(self.ser, command)
            self.log_message("群读启动命令已发送")
            self.log_message("开始群读")

            # 创建并启动读卡线程
            self.read_thread = SerialReadThread(self.ser)
            self.read_thread.card_readed.connect(self.handle_card_read)
            self.read_thread.read_failed.connect(self.handle_read_failed)
            self.read_thread.error_occurred.connect(self.handle_read_error)
            self.read_thread.start()

            self.group_read_active = True
            self.main_page.btn_start_read.setEnabled(False)
            self.main_page.btn_stop_read.setEnabled(True)
        except Exception as e:
            self.handle_serial_error(str(e))

    def handle_card_read(self, card_number):
        """
        处理读取到的卡号
        参数:
            card_number: 读取到的卡号字符串
        """
        if self.group_read_active:
            self.read_failed_logged = False
            self.main_page.add_card_to_table(card_number)

            # 如果匹配功能激活，进行卡号匹配
            if self.matching_active and self.target_number and not self.match_found:
                # 确保使用原始EPC格式进行匹配
                if isinstance(card_number, dict) and 'epc' in card_number:
                    # 尝试匹配
                    match_result = self.match_page.match_with_database(card_number['epc'])
                    if match_result:
                        self.match_found = True
                        self.match_timer.stop()  # 停止未匹配提示
                        # 显示匹配成功信息
                        self.match_page.append_result(
                            f"[{QDateTime.currentDateTime().toString('HH:mm:ss')}] 找到匹配！\n"
                            f"目标数字: {self.target_number}\n"
                            f"完整EPC: {card_number['epc']}\n"
                            f"信号强度: {card_number['rssi']} dBm\n"
                            f"------------------------"
                        )
                        # 找到匹配后自动停止群读并重置匹配页面状态
                        self.stop_reading()
                        self.match_page.reset_match_state()

            # 如果搜索页面正在搜索，尝试匹配
            if hasattr(self.search_page, 'btn_stop') and self.search_page.btn_stop.isEnabled():
                # 如果停止按钮可用（即正在搜索），则进行匹配
                if isinstance(card_number, dict) and 'epc' in card_number:
                    # 尝试在搜索页面中匹配
                    match_result = self.search_page.match_with_database(card_number)
                    if match_result:
                        self.search_page.add_match_result(card_number, match_result)

    def handle_read_failed(self):
        """
        处理读卡失败的情况
        """
        if self.group_read_active and not self.read_failed_logged:
            self.log_message("群读未识别到标签，读取卡号失败")
            self.read_failed_logged = True

    def handle_read_error(self, error_message):
        """
        处理读卡过程中的错误
        参数:
            error_message: 错误信息
        """
        self.log_message(f"读取线程错误: {error_message}")
        self.stop_reading()

    def stop_reading(self):
        """
        停止群读模式
        清理相关资源并更新界面状态
        """
        if not self.ser or not self.ser.is_open:
            self.log_message("设备未连接，无法结束群读")
            return

        self.group_read_active = False
        self.match_timer.stop()  # 停止未匹配提示定时器

        command = bytearray([0xBB, 0x00, 0x28, 0x00, 0x00, 0x28, 0x7E])
        try:
            send_command(self.ser, command)
            self.log_message("结束群读命令已发送")

            # 停止读卡线程
            if self.read_thread:
                try:
                    self.read_thread.card_readed.disconnect(self.handle_card_read)
                    self.read_thread.read_failed.disconnect(self.handle_read_failed)
                    self.read_thread.error_occurred.disconnect(self.handle_read_error)
                except TypeError:
                    pass

                self.read_thread.stop()
                self.read_thread = None

            self.log_message("群读已结束")
            self.main_page.btn_start_read.setEnabled(True)
            self.main_page.btn_stop_read.setEnabled(False)

            # 停止匹配
            self.matching_active = False
            self.target_number = None
        except Exception as e:
            self.handle_serial_error(str(e))

    def get_current_gain(self):
        """
        获取当前RFID读写器的增益值
        """
        if not self.ser or not self.ser.is_open:
            self.log_message("设备未连接，无法获取增益")
            return

        command = bytearray([0xBB, 0x00, 0xB7, 0x00, 0x00, 0xB7, 0x7E])
        try:
            response = send_command(self.ser, command)
            if response and len(response) >= 9:
                expected_header = bytearray([0xBB, 0x01, 0xB7, 0x00, 0x02])
                if response.startswith(expected_header):
                    # 解析增益值
                    pow_msb = response[5]
                    pow_lsb = response[6]
                    pow_value = (pow_msb << 8) | pow_lsb
                    self.gain = pow_value / 100
                    # 更新功率设置页面的标签
                    self.blank_page.label_power.setText(f"当前功率/增益: {self.gain} dBm")
                    self.log_message(f"当前增益: {self.gain} dBm")
                else:
                    self.blank_page.label_power.setText("当前功率/增益: 获取失败")
                    self.log_message("响应格式不正确，无法解析增益")
            else:
                self.blank_page.label_power.setText("当前功率/增益: 获取失败")
                if response:
                    self.log_message(f"接收到响应长度: {len(response)}，数据: {response.hex().upper()}")
                self.log_message("未收到设备增益响应 请检查连接设备是否为R200系列芯片 软件仅支持R200系列UHF读卡器使用！")
        except Exception as e:
            self.handle_serial_error(str(e))

    def write_card(self):
        """
        向RFID标签写入数据
        """
        if not self.ser or not self.ser.is_open:
            self.log_message("设备未连接，无法写入数据")
            return

        input_data = self.write_page.write_input.text()
        if not input_data or len(input_data) > 16:
            self.log_message("输入数据无效，请输入16字节以内的16进制字符串")
            return

        try:
            data_bytes = bytes.fromhex(input_data)
        except ValueError:
            self.log_message("输入数据格式错误，请输入16进制字符串")
            return

        # 构建写卡命令
        command = bytearray([0xBB, 0x00, 0x49, 0x00, 0x11, 0x00, 0x00, 0x00, 0x00, 0x03, 0x00, 0x00, 0x00,
                             len(data_bytes)]) + data_bytes
        command.append(sum(command[1:]) % 256)  # 添加校验和
        command.append(0x7E)  # 添加结束符

        try:
            response = send_command(self.ser, command)
            if response.startswith(bytearray([0xBB, 0x01, 0x49])):
                self.log_message("写入成功")
            else:
                self.log_message("写入失败")
        except Exception as e:
            self.handle_serial_error(str(e))

    def clear_log(self):
        """
        清空所有日志显示
        """
        self.main_page.clear_log()
        self.write_page.clear_log()
        self.log_count = 0

    def handle_serial_error(self, error_msg):
        """
        处理串口通信错误
        参数:
            error_msg: 错误信息
        """
        # 检查是否是设备断开连接的错误
        if ("PermissionError" in error_msg and
                ("设备不识别此命令" in error_msg or
                 "拒绝访问" in error_msg or
                 "ClearCommError failed" in error_msg)):

            self.log_message("检测到设备断开连接")

            # 如果正在群读,先停止群读线程
            if self.group_read_active:
                if self.read_thread:
                    self.read_thread.stop()
                    self.read_thread.wait()
                    self.read_thread = None
                self.group_read_active = False
                self.main_page.btn_start_read.setEnabled(True)
                self.main_page.btn_stop_read.setEnabled(False)

            # 关闭串口连接
            if self.ser:
                try:
                    self.ser.close()
                except (serial.SerialException, IOError) as e:
                    self.log_message(f"关闭串口时出现错误: {str(e)}")
                self.ser = None

            # 更新界面状态
            self.main_page.label_status.setText("状态: 设备已断开 ⚠️")
            self.main_page.label_status.setStyleSheet("""
                QLabel {
                    font-size: 16px;
                    font-weight: bold;
                    color: #FF6B6B;
                    padding: 0px;
                    margin: 0px;
                }
            """)
            self.main_page.btn_connect_disconnect.setText("连接设备")
            self.main_page.btn_connect_disconnect.setStyleSheet("""
                QPushButton {
                    background-color: #ffcccc;
                    border: none;
                    border-radius: 4px;
                    padding: 4px;
                }
                QPushButton:hover {
                    background-color: #ff9999;
                }
            """)
            # 更新功率设置页面的标签
            self.blank_page.label_power.setText("当前功率/增益: --")

            # 自动扫描可用端口
            self.scan_ports()
        else:
            # 其他错误只记录日志
            self.log_message(f"串口通信错误: {error_msg}")

    def set_select_mode(self, mode):
        """
        设置Select模式
        参数:
            mode: 0x00=所有操作都使用Select
                 0x01=不使用Select
                 0x02=除轮询外的操作使用Select
        """
        if not self.ser or not self.ser.is_open:
            self.log_message("设备未连接，无法设置Select模式")
            return

        # 构建命令帧
        command = bytearray([
            0xBB,  # Header
            0x00,  # Type
            0x12,  # Command
            0x00,  # PL(MSB)
            0x01,  # PL(LSB)
            mode  # Mode
        ])
        # 计算校验和（从Type到最后一个参数的累加和的最低字节）
        checksum = sum(command[1:6]) & 0xFF  # 使用 & 0xFF 取最低字节
        command.extend([checksum, 0x7E])

        try:
            # 发送命令并获取响应
            response = send_command(self.ser, command)

            # 打印发送的命令和接收的响应（用于调试）
            self.log_message(f"发送Select模式命令: {' '.join([f'{b:02X}' for b in command])}")
            if response:
                self.log_message(f"收到响应数据: {' '.join([f'{b:02X}' for b in response])}")

            # 验证响应帧
            if (response and
                    len(response) >= 8 and
                    response[0] == 0xBB and  # Header
                    response[1] == 0x01 and  # Type
                    response[2] == 0x12 and  # Command (响应命令与请求命令相同)
                    response[3] == 0x00 and  # PL(MSB)
                    response[4] == 0x01 and  # PL(LSB)
                    response[5] == 0x00 and  # Data (0x00表示执行成功)
                    response[7] == 0x7E):  # End

                # 验证校验和（从Type到Data的累加和的最低字节）
                calc_checksum = sum(response[1:6]) & 0xFF
                if calc_checksum != response[6]:
                    self.log_message(f"警告：响应校验和错误 (计算值={calc_checksum:02X}, 接收值={response[6]:02X})")

                self.select_mode = mode
                mode_desc = {
                    0x00: "所有操作使用Select",
                    0x01: "不使用Select",
                    0x02: "除轮询外的操作使用Select"
                }
                self.log_message(f"Select模式已设置为: {mode_desc.get(mode, '未知模式')}")
            else:
                error_msg = "设置Select模式失败: "
                if not response:
                    error_msg += "未收到响应"
                elif len(response) < 8:
                    error_msg += f"响应长度错误 (期望8字节，实际{len(response)}字节)"
                else:
                    error_msg += "响应格式错误"
                self.log_message(error_msg)
        except Exception as e:
            self.handle_serial_error(str(e))

    def verify_select_and_read(self):
        """
        验证SELECT设置和读卡操作是否匹配成功
        返回:
            bool: 验证是否成功
        """
        if not self.ser or not self.ser.is_open:
            self.log_message("设备未连接，无法验证SELECT参数")
            return False

        # 首先获取当前的SELECT参数
        if not self.select_param:
            self.log_message("未设置SELECT参数")
            return False

        # 执行读卡操作
        command = bytearray([0xBB, 0x00, 0x22, 0x00, 0x00, 0x22, 0x7E])
        try:
            response = send_command(self.ser, command)
            if response and len(response) >= 20:  # 确保响应长度足够
                # 从响应中提取EPC
                epc_bytes = response[8:20] if response[2] == 0x22 else response[9:21]
                read_epc = ' '.join([f"{b:02X}" for b in epc_bytes])

                # 比较SELECT参数和读取到的EPC
                if self.select_param.replace(" ", "") == read_epc.replace(" ", ""):
                    self.log_message("SELECT设置和读卡操作匹配成功")
                    return True
                else:
                    self.log_message(f"SELECT设置和读取到的EPC不匹配\n设置值: {self.select_param}\n读取值: {read_epc}")
                    return False
        except Exception as e:
            self.log_message(f"验证过程出错: {str(e)}")
            return False

        return False

    def set_select_params(self, target_epc=None):
        """
        设置Select参数
        参数:
            target_epc: 目标EPC，如果为None则清除Select
        """
        if not self.ser or not self.ser.is_open:
            self.log_message("设备未连接，无法设置Select参数")
            return

        if target_epc:
            try:
                # 移除空格并转换为字节数组
                epc_bytes = bytes.fromhex(target_epc.replace(" ", ""))

                # 检查EPC长度是否为12字节（96位）
                if len(epc_bytes) != 12:
                    self.log_message("错误：EPC必须为12字节（96位）")
                    return

                # 构建命令帧，固定参数按照文档要求设置
                command = bytearray([
                    0xBB,  # Header
                    0x00,  # Type
                    0x0C,  # Command
                    0x00,  # PL(MSB)
                    0x13,  # PL(LSB) = 19字节参数长度
                    0x01,  # SelParam (Target=000, Action=000, MemBank=01)
                    0x00, 0x00, 0x00, 0x20,  # Ptr=0x00000020 (从EPC存储区开始)
                    0x60,  # MaskLen (固定96位)
                    0x00  # Truncate (禁用)
                ])

                # 添加12字节的Mask数据（EPC）
                command.extend(epc_bytes)

                # 计算校验和（从Type到最后一个参数的累加和的最低字节）
                checksum = sum(command[1:24]) & 0xFF
                command.append(checksum)  # 添加校验和
                command.append(0x7E)  # 添加结束符

                # 发送命令并获取响应
                response = send_command(self.ser, command)

                # 验证响应
                if (response and
                        len(response) >= 8 and
                        response[0] == 0xBB and
                        response[1] == 0x01 and
                        response[2] == 0x0C and
                        response[3] == 0x00 and
                        response[4] == 0x01 and
                        response[5] == 0x00):

                    self.select_param = target_epc
                    self.log_message(f"成功设置Select参数，目标EPC: {target_epc}")

                    # 设置Select模式为除轮询外的操作使用Select (0x02)
                    self.set_select_mode(0x02)
                    # 更新界面的Select模式下拉框
                    self.main_page.combo_select_mode.setCurrentIndex(2)

                    # 设置完成后立即验证
                    if self.verify_select_and_read():
                        self.log_message("SELECT参数验证成功")
                    else:
                        self.log_message("SELECT参数验证失败，请检查设置")
                else:
                    self.log_message("设置Select参数失败")

            except ValueError as e:
                self.log_message(f"EPC格式错误: {str(e)}")
            except Exception as e:
                self.handle_serial_error(str(e))
        else:
            # 清除Select参数时设置模式为0x01（不使用Select）
            self.set_select_mode(0x01)
            self.select_param = None
            self.main_page.combo_select_mode.setCurrentIndex(1)  # 更新界面
            self.log_message("已清除Select参数")

    def get_select_params(self):
        """
        获取当前的Select参数
        """
        if not self.ser or not self.ser.is_open:
            self.log_message("设备未连接，无法获取Select参数")
            return

        command = bytearray([0xBB, 0x00, 0x0B, 0x00, 0x00, 0x0B, 0x7E])

        try:
            response = send_command(self.ser, command)

            # 检查响应的完整性
            if not response or len(response) < 26:  # 完整响应应该是26字节
                self.log_message(f"响应数据长度不正确: 期望26字节，实际收到{len(response) if response else 0}字节")
                return

            # 验证响应帧格式
            if (response[0] != 0xBB or  # 帧头
                    response[1] != 0x01 or  # 类型
                    response[2] != 0x0B or  # 命令码
                    response[3] != 0x00 or  # PL(MSB)
                    response[4] != 0x13):  # PL(LSB)
                self.log_message("响应帧格式错误")
                return

            # 验证固定参数
            sel_param = response[5]
            if sel_param != 0x01:  # Target=000, Action=000, MemBank=01
                self.log_message(f"警告：SelParam不是预期值 (当前值={sel_param:02X}, 预期值=01)")

            # 验证指针值
            ptr = (response[6] << 24) | (response[7] << 16) | (response[8] << 8) | response[9]
            if ptr != 0x00000020:
                self.log_message(f"警告：指针位置不是预期值 (当前值=0x{ptr:08X}, 预期值=0x00000020)")

            # 验证Mask长度
            mask_len = response[10]
            if mask_len != 0x60:
                self.log_message(f"警告：Mask长度不是预期值 (当前值=0x{mask_len:02X}, 预期值=0x60)")

            # 验证Truncate
            truncate = response[11]
            if truncate != 0x00:
                self.log_message(f"警告：Truncate不是预期值 (当前值=0x{truncate:02X}, 预期值=0x00)")

            # 获取Mask值（12字节EPC）
            mask_bytes = response[12:24]
            mask = ' '.join([f"{b:02X}" for b in mask_bytes])

            # 更新界面状态
            self.main_page.target_epc_input.setText(mask)
            self.log_message(f"当前Select参数 EPC值: {mask}")

        except Exception as e:
            self.handle_serial_error(str(e))

    def on_select_mode_changed(self, index):
        """
        处理Select模式改变事件
        """
        mode_map = {0: 0x00, 1: 0x01, 2: 0x02}
        self.set_select_mode(mode_map[index])

    def on_set_select_clicked(self):
        """
        处理设置Select参数按钮点击事件
        """
        target_epc = self.main_page.target_epc_input.text().strip()
        if not target_epc:
            self.log_message("请输入目标EPC")
            return
        self.set_select_params(target_epc)

    def on_clear_select_clicked(self):
        """
        处理清除Select参数按钮点击事件
        """
        self.set_select_params(None)
        self.main_page.target_epc_input.clear()

    def show_matching_status(self):
        """
        显示匹配状态提示
        """
        if self.matching_active and not self.match_found:
            self.match_page.append_result("暂未匹配到正确设备...")

    def start_card_matching(self, target_number):
        """
        开始卡号匹配过程
        参数:
            target_number: 要匹配的目标数字
        """
        self.target_number = target_number
        self.matching_active = True
        self.match_found = False  # 重置匹配标志
        self.match_page.append_result(f"开始匹配目标数字: {target_number}")

        # 启动未匹配提示定时器
        self.match_timer.start()

        # 如果当前没有在群读，自动开始群读
        if not self.group_read_active:
            self.read_cards()

    def send_command(self, command):
        """
        发送命令到设备并获取响应
        参数:
            command: 要发送的命令字节数组
        返回:
            bytes: 设备的响应数据
        """
        if not self.ser or not self.ser.is_open:
            raise Exception("设备未连接")

        try:
            # 清空接收缓冲区
            self.ser.reset_input_buffer()

            # 发送命令
            self.ser.write(command)

            # 等待响应
            time.sleep(0.1)  # 等待设备处理命令

            # 读取响应
            response = bytearray()
            while self.ser.in_waiting:
                byte = self.ser.read()
                response.extend(byte)
                if byte == b'\x7E':  # 检测到结束符
                    break

            return bytes(response)
        except Exception as e:
            raise Exception(f"发送命令失败: {str(e)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 添加 Fluent 翻译器
    translator = FluentTranslator()
    app.installTranslator(translator)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
