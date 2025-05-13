from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QSplitter, QTableWidgetItem, QHeaderView, QAbstractItemView, QMenu
)
from qfluentwidgets import (
    SubtitleLabel, PushButton, ComboBox, TextEdit,
    TableWidget, TableItemDelegate, LineEdit
)


class MainPage(QWidget):
    """
    主页面类
    实现RFID读写器的主要操作界面，包括设备连接、功率设置、读卡操作等功能
    """

    def __init__(self, parent=None):
        """
        初始化主页面
        参数:
            parent: 父窗口对象
        """
        super().__init__(parent=parent)
        # 设置页面标识
        self.setObjectName("mainPage")

        # 初始化控件变量
        self.label_status = None  # 状态标签
        self.btn_clear_log = None  # 清空日志按钮
        self.btn_scan_ports = None  # 扫描端口按钮
        self.combo_ports = None  # 端口选择下拉框
        self.btn_connect_disconnect = None  # 连接/断开按钮
        self.label_power = None  # 功率显示标签
        self.combo_power = None  # 功率选择下拉框
        self.btn_set_power = None  # 设置功率按钮
        self.btn_read_once = None  # 单次读卡按钮
        self.btn_start_read = None  # 开始群读按钮
        self.btn_stop_read = None  # 停止群读按钮
        self.btn_get_gain = None  # 获取增益按钮
        self.btn_exit = None  # 退出按钮
        self.card_table = None  # 卡号显示表格
        self.log_text_edit = None  # 日志显示区域
        self.btn_clear_cards = None  # 清除群读数据按钮
        self.combo_select_mode = None  # Select模式选择下拉框
        self.target_epc_input = None  # 目标EPC输入框
        self.btn_set_select = None  # 设置Select按钮
        self.btn_clear_select = None  # 清除Select按钮
        self.btn_get_select = None  # 获取Select参数按钮

        # 初始化界面
        self.setup_ui()

    def setup_ui(self):
        """
        初始化用户界面
        设置布局和控件
        """
        # 创建主布局
        main_layout = QHBoxLayout()

        # 创建左侧功能区
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setSpacing(10)  # 减小组件间距
        left_layout.setContentsMargins(10, 30, 10, 10)  # 减小边距

        # 添加状态标签
        self.label_status = SubtitleLabel("状态: 未连接 😢", self)
        self.label_status.setObjectName("statusLabel")
        self.label_status.setFixedHeight(32)
        self.label_status.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #303030;
                padding: 0px;
                margin: 0px;
            }
        """)
        left_layout.addWidget(self.label_status)

        # 创建连接控制组
        connect_group = QGroupBox("连接控制", self)
        connect_layout = QVBoxLayout()
        connect_layout.setSpacing(5)  # 减小内部间距
        connect_layout.setContentsMargins(5, 5, 5, 5)  # 减小内部边距

        # 创建按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(5)

        # 添加清空日志按钮
        self.btn_clear_log = PushButton("清空日志", self)
        self.btn_clear_log.setFixedHeight(28)
        button_layout.addWidget(self.btn_clear_log)

        # 添加扫描端口按钮
        self.btn_scan_ports = PushButton("扫描COM端口", self)
        self.btn_scan_ports.setFixedHeight(28)
        button_layout.addWidget(self.btn_scan_ports)

        connect_layout.addLayout(button_layout)

        # 创建端口选择下拉框
        self.combo_ports = ComboBox(self)
        self.combo_ports.setFixedHeight(28)
        connect_layout.addWidget(self.combo_ports)

        # 创建连接/断开按钮
        self.btn_connect_disconnect = PushButton("连接设备", self)
        self.btn_connect_disconnect.setEnabled(False)
        self.btn_connect_disconnect.setFixedHeight(28)
        self.btn_connect_disconnect.setStyleSheet("""
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
        connect_layout.addWidget(self.btn_connect_disconnect)

        connect_group.setLayout(connect_layout)
        left_layout.addWidget(connect_group)

        # 创建操作按钮组
        action_group = QGroupBox("操作", self)
        action_layout = QVBoxLayout()
        action_layout.setSpacing(8)  # 增加组件间距
        action_layout.setContentsMargins(5, 5, 5, 5)

        # 添加Select控制组
        select_group = QGroupBox("标签筛选", self)
        select_layout = QVBoxLayout()
        select_layout.setSpacing(4)  # 减小内部间距
        select_layout.setContentsMargins(5, 5, 5, 5)  # 减小边距

        # 添加Select模式选择下拉框
        self.combo_select_mode = ComboBox(self)
        self.combo_select_mode.addItems([
            "所有操作使用Select",
            "不使用Select",
            "除轮询外使用Select"
        ])
        self.combo_select_mode.setCurrentIndex(1)
        self.combo_select_mode.setFixedHeight(28)  # 减小高度
        select_layout.addWidget(self.combo_select_mode)

        # 添加目标EPC输入框
        self.target_epc_input = LineEdit(self)
        self.target_epc_input.setPlaceholderText("输入目标EPC（空格分隔）")
        self.target_epc_input.setFixedHeight(28)  # 减小高度
        select_layout.addWidget(self.target_epc_input)

        # 创建两行按钮布局
        select_buttons_layout = QVBoxLayout()
        select_buttons_layout.setSpacing(4)

        # 第一行按钮
        select_buttons_row1 = QHBoxLayout()
        select_buttons_row1.setSpacing(4)

        self.btn_set_select = PushButton("设置Select", self)
        self.btn_set_select.setFixedHeight(26)
        select_buttons_row1.addWidget(self.btn_set_select)

        self.btn_clear_select = PushButton("清除Select", self)
        self.btn_clear_select.setFixedHeight(26)
        select_buttons_row1.addWidget(self.btn_clear_select)

        select_buttons_layout.addLayout(select_buttons_row1)

        # 第二行按钮
        self.btn_get_select = PushButton("获取Select", self)
        self.btn_get_select.setFixedHeight(26)
        select_buttons_layout.addWidget(self.btn_get_select)

        select_layout.addLayout(select_buttons_layout)
        select_group.setLayout(select_layout)
        action_layout.addWidget(select_group)

        # 创建读卡操作按钮组
        read_buttons_group = QGroupBox("读卡操作", self)
        read_buttons_layout = QVBoxLayout()
        read_buttons_layout.setSpacing(4)
        read_buttons_layout.setContentsMargins(5, 5, 5, 5)

        # 第一行：单次读卡和群读按钮
        read_row1 = QHBoxLayout()
        read_row1.setSpacing(4)

        self.btn_read_once = PushButton("单次读取", self)
        self.btn_read_once.setFixedHeight(26)
        read_row1.addWidget(self.btn_read_once)

        self.btn_start_read = PushButton("群读卡号", self)
        self.btn_start_read.setFixedHeight(26)
        read_row1.addWidget(self.btn_start_read)

        read_buttons_layout.addLayout(read_row1)

        # 第二行：停止群读和获取增益按钮
        read_row2 = QHBoxLayout()
        read_row2.setSpacing(4)

        self.btn_stop_read = PushButton("结束群读", self)
        self.btn_stop_read.setEnabled(False)
        self.btn_stop_read.setFixedHeight(26)
        read_row2.addWidget(self.btn_stop_read)

        self.btn_get_gain = PushButton("获取增益", self)
        self.btn_get_gain.setFixedHeight(26)
        read_row2.addWidget(self.btn_get_gain)

        read_buttons_layout.addLayout(read_row2)
        read_buttons_group.setLayout(read_buttons_layout)
        action_layout.addWidget(read_buttons_group)

        # 添加退出按钮
        self.btn_exit = PushButton("退出", self)
        self.btn_exit.setFixedHeight(28)
        action_layout.addWidget(self.btn_exit)

        action_group.setLayout(action_layout)
        left_layout.addWidget(action_group)

        # 添加弹性空间
        left_layout.addStretch()

        left_widget.setLayout(left_layout)
        left_widget.setFixedWidth(280)  # 减小左侧区域宽度

        # 创建右侧显示区域
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(5, 30, 5, 5)

        # 创建群读卡号显示组
        card_group = QGroupBox("群读卡号", self)
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(5, 5, 5, 5)

        # 添加清除群读数据按钮
        self.btn_clear_cards = PushButton("清除群读数据", self)
        self.btn_clear_cards.clicked.connect(self.clear_card_table)
        card_layout.addWidget(self.btn_clear_cards)

        # 创建卡号显示表格
        self.card_table = TableWidget(self)
        self.card_table.setColumnCount(7)  # 修改为7列
        self.card_table.setHorizontalHeaderLabels(["序号", "PC", "EPC", "CRC", "RSSI(dBm)", "次数", "成功率(%)"])
        self.card_table.setItemDelegate(TableItemDelegate(self.card_table))
        self.card_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.card_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.card_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.card_table.horizontalHeader().setStretchLastSection(False)

        # 启用右键菜单
        self.card_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.card_table.customContextMenuRequested.connect(self.show_context_menu)
        
        # 添加双击事件处理
        self.card_table.doubleClicked.connect(self.on_table_double_clicked)

        # 设置表格列宽
        self.card_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # 序号列自适应
        self.card_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # PC列自适应
        self.card_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # EPC列拉伸
        self.card_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # CRC列自适应
        self.card_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # RSSI列自适应
        self.card_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # 次数列自适应
        self.card_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # 成功率列自适应

        # 设置表格的最大高度,使其能够显示更多行
        self.card_table.setMinimumHeight(300)  # 设置最小高度
        self.card_table.verticalHeader().setVisible(False)  # 隐藏垂直表头
        self.card_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)  # 需要时显示垂直滚动条

        card_layout.addWidget(self.card_table)
        card_group.setLayout(card_layout)
        right_layout.addWidget(card_group)

        # 创建日志显示组
        log_group = QGroupBox("日志", self)
        log_layout = QVBoxLayout()
        log_layout.setContentsMargins(5, 5, 5, 5)

        # 创建日志文本框
        self.log_text_edit = TextEdit(self)
        self.log_text_edit.setReadOnly(True)
        log_layout.addWidget(self.log_text_edit)
        log_group.setLayout(log_layout)
        right_layout.addWidget(log_group)

        right_widget.setLayout(right_layout)

        # 创建分隔器，实现左右两侧可调整布局
        splitter = QSplitter()
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 0)  # 左侧不自动拉伸
        splitter.setStretchFactor(1, 1)  # 右侧自动拉伸

        # 设置左侧固定宽度
        left_widget.setFixedWidth(350)

        # 禁用分隔器拖动功能
        splitter.setHandleWidth(0)

        # 设置主布局
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

    def append_log(self, message):
        """
        添加日志消息到显示区域
        参数:
            message: 要添加的日志消息
        """
        if self.log_text_edit:
            self.log_text_edit.append(message)

    def clear_log(self):
        """
        清空日志显示区域的内容
        """
        if self.log_text_edit:
            self.log_text_edit.clear()

    def clear_card_table(self):
        """
        清空卡号显示表格的内容
        """
        if self.card_table:
            self.card_table.setRowCount(0)

    def add_card_to_table(self, card_info):
        """
        添加卡号到显示表格
        参数:
            card_info: 包含卡片信息的字典，包括PC、EPC、CRC、RSSI等字段
        """
        if not self.card_table:
            return

        # 使用EPC作为唯一标识
        epc = card_info['epc']

        # 查找卡号是否已存在
        for row in range(self.card_table.rowCount()):
            if self.card_table.item(row, 2).text() == epc:  # EPC在第3列
                # 已存在则更新计数和RSSI
                count_item = self.card_table.item(row, 5)
                count = int(count_item.text())
                new_count = count + 1
                count_item.setText(str(new_count))
                # 更新RSSI
                self.card_table.item(row, 4).setText(card_info['rssi'])
                # 更新成功率
                success_rate = (new_count / (new_count + count)) * 100
                self.card_table.item(row, 6).setText(f"{success_rate:.3f}")
                return

        # 添加新卡号记录
        row = self.card_table.rowCount()
        self.card_table.insertRow(row)

        # 设置各列数据
        self.card_table.setItem(row, 0, QTableWidgetItem(f"{row + 1:02d}"))  # 序号，两位数字格式
        self.card_table.setItem(row, 1, QTableWidgetItem(card_info['pc']))  # PC
        self.card_table.setItem(row, 2, QTableWidgetItem(epc))  # EPC
        self.card_table.setItem(row, 3, QTableWidgetItem(card_info['crc']))  # CRC
        self.card_table.setItem(row, 4, QTableWidgetItem(card_info['rssi']))  # RSSI(dBm)
        self.card_table.setItem(row, 5, QTableWidgetItem("1"))  # 初始计数
        self.card_table.setItem(row, 6, QTableWidgetItem("100.000"))  # 初始成功率

        # 只在新增卡号时滚动到底部
        self.card_table.scrollToBottom()

    def show_context_menu(self, pos):
        """
        显示右键菜单
        参数:
            pos: 鼠标点击位置
        """
        # 获取当前选中的行
        row = self.card_table.rowAt(pos.y())
        if row < 0:
            return

        # 创建右键菜单
        menu = QMenu(self)
        copy_action = menu.addAction("复制卡号信息")

        # 显示菜单并获取用户选择的动作
        action = menu.exec(self.card_table.viewport().mapToGlobal(pos))

        if action == copy_action:
            self.copy_card_info(row)

    def copy_card_info(self, row):
        """
        复制指定行的卡号信息
        参数:
            row: 要复制的行号
        """
        # 获取各列的标题和内容
        headers = []
        values = []
        for col in range(1, 7):  # 复制除序号外的所有列
            header = self.card_table.horizontalHeaderItem(col).text()
            value = self.card_table.item(row, col).text()
            headers.append(header)
            values.append(value)

        # 组合成要复制的文本
        copy_text = '\n'.join([
            '\t'.join(headers),  # 标题行
            '\t'.join(values)  # 内容行
        ])

        # 复制到剪贴板
        clipboard = QApplication.clipboard()
        clipboard.setText(copy_text)

        # 在日志中显示复制成功信息
        self.append_log(f"已复制第 {row + 1:02d} 行卡号信息到剪贴板")

    def on_table_double_clicked(self, index):
        """
        处理表格双击事件
        参数:
            index: 被双击的单元格索引
        """
        # 获取被双击的行
        row = index.row()
        
        # 获取该行的EPC值（第3列）
        epc_item = self.card_table.item(row, 2)
        if epc_item:
            # 将EPC值设置到SELECT输入框
            self.target_epc_input.setText(epc_item.text())
            self.append_log(f"已将第 {row + 1:02d} 行的EPC值 {epc_item.text()} 填入SELECT输入框")
