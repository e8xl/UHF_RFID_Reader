import os
import platform
import socket
import sqlite3
from typing import Optional

from PySide6.QtCore import Qt, QTimer, QDateTime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QTableWidgetItem, QHeaderView, QAbstractItemView
)
from qfluentwidgets import (
    SearchLineEdit, PushButton,
    TableWidget, TableItemDelegate, InfoBar,
    InfoBarPosition, FluentIcon as FIF,
    CalendarPicker, TimePicker
)


class AssetPage(QWidget):
    """扫描历史记录页面类"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent=parent)
        self.setObjectName("assetPage")

        # 初始化实例变量
        self.search_edit: Optional[SearchLineEdit] = None
        self.refresh_btn: Optional[PushButton] = None
        self.total_label: Optional[QLabel] = None
        self.current_page_label: Optional[QLabel] = None
        self.table: Optional[TableWidget] = None
        self.prev_btn: Optional[PushButton] = None
        self.next_btn: Optional[PushButton] = None
        self.start_date: Optional[CalendarPicker] = None
        self.start_time: Optional[TimePicker] = None
        self.end_date: Optional[CalendarPicker] = None
        self.end_time: Optional[TimePicker] = None

        # 数据库连接
        self.db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'asset_report.db')

        # 分页相关
        self.page_size = 50  # 每页显示的记录数
        self.current_page = 1
        self.total_records = 0
        self.current_search = ""  # 当前搜索条件

        # 初始化UI
        self.setup_ui()

        # 设置自动刷新定时器
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(5000)  # 每5秒自动刷新一次

    def setup_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 40, 20, 20)  # 增加顶部边距
        layout.setSpacing(16)  # 增加组件间距

        # 顶部控制区域
        control_group = QGroupBox("搜索控制", self)
        control_layout = QVBoxLayout()
        control_layout.setContentsMargins(12, 12, 12, 12)

        # 搜索条件区域
        search_layout = QHBoxLayout()
        search_layout.setSpacing(8)

        # 搜索框
        self.search_edit = SearchLineEdit(self)
        self.search_edit.setPlaceholderText("输入EPC编号或资产描述搜索...")
        self.search_edit.textChanged.connect(self.on_search_changed)
        search_layout.addWidget(self.search_edit)

        # 时间范围选择
        date_layout = QHBoxLayout()
        date_layout.setSpacing(4)  # 减小控件间距

        # 开始时间
        start_time_layout = QHBoxLayout()
        start_time_layout.setSpacing(4)
        start_time_layout.addWidget(QLabel("开始:", self))

        # 日期选择器
        self.start_date = CalendarPicker(self)
        self.start_date.setFixedWidth(130)
        today = QDateTime.currentDateTime().date()
        self.start_date.setDate(today)
        self.start_date.dateChanged.connect(self.on_date_changed)  # 添加日期变更事件
        start_time_layout.addWidget(self.start_date)

        # 时间选择器
        self.start_time = TimePicker(self)
        self.start_time.setFixedWidth(100)
        start_time = QDateTime.currentDateTime().time()
        start_time.setHMS(0, 0, 0)  # 设置为00:00:00
        self.start_time.setTime(start_time)
        self.start_time.timeChanged.connect(self.on_time_changed)  # 添加时间变更事件
        start_time_layout.addWidget(self.start_time)

        date_layout.addLayout(start_time_layout)

        # 添加一个小的间隔
        date_layout.addSpacing(10)

        # 结束时间
        end_time_layout = QHBoxLayout()
        end_time_layout.setSpacing(4)
        end_time_layout.addWidget(QLabel("结束:", self))

        # 日期选择器
        self.end_date = CalendarPicker(self)
        self.end_date.setFixedWidth(130)
        self.end_date.setDate(today)
        self.end_date.dateChanged.connect(self.on_date_changed)  # 添加日期变更事件
        end_time_layout.addWidget(self.end_date)

        # 时间选择器
        self.end_time = TimePicker(self)
        self.end_time.setFixedWidth(100)
        end_time = QDateTime.currentDateTime().time()
        end_time.setHMS(23, 59, 59)  # 设置为23:59:59
        self.end_time.setTime(end_time)
        self.end_time.timeChanged.connect(self.on_time_changed)  # 添加时间变更事件
        end_time_layout.addWidget(self.end_time)

        date_layout.addLayout(end_time_layout)

        # 添加一个弹性空间，将刷新按钮推到右边
        date_layout.addStretch()

        # 刷新按钮
        self.refresh_btn = PushButton('刷新数据', self, FIF.SYNC)
        self.refresh_btn.clicked.connect(self.manual_refresh)
        date_layout.addWidget(self.refresh_btn)

        control_layout.addLayout(search_layout)
        control_layout.addLayout(date_layout)
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)

        # 统计信息区域
        stats_group = QGroupBox("统计信息", self)
        stats_layout = QHBoxLayout()
        stats_layout.setContentsMargins(12, 12, 12, 12)

        self.total_label = QLabel("总记录数: 0", self)
        stats_layout.addWidget(self.total_label)

        self.current_page_label = QLabel("当前页: 1", self)
        stats_layout.addWidget(self.current_page_label)

        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        # 数据表格
        self.table = TableWidget(self)
        self.table.setItemDelegate(TableItemDelegate(self.table))
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)

        # 设置表格列
        self.table.setColumnCount(5)  # 增加到5列
        self.table.setHorizontalHeaderLabels([
            "序号", "EPC编号", "扫描时间", "设备名称", "资产描述"
        ])

        # 设置列宽
        self.table.horizontalHeader().resizeSection(0, 54)  # 序号列
        self.table.horizontalHeader().resizeSection(1, 128)  # EPC编号列
        self.table.horizontalHeader().resizeSection(2, 176)  # 扫描时间列
        self.table.horizontalHeader().resizeSection(3, 150)  # 设备名称列

        layout.addWidget(self.table)

        # 分页控制
        page_control = QHBoxLayout()
        page_control.setSpacing(8)

        self.prev_btn = PushButton('上一页', self, FIF.PAGE_LEFT)
        self.prev_btn.clicked.connect(self.prev_page)
        page_control.addWidget(self.prev_btn)

        self.next_btn = PushButton('下一页', self, FIF.PAGE_RIGHT)
        self.next_btn.clicked.connect(self.next_page)
        page_control.addWidget(self.next_btn)

        layout.addLayout(page_control)

        # 初始加载数据
        self.refresh_data()

    def manual_refresh(self):
        """手动刷新数据"""
        self.refresh_btn.setEnabled(False)  # 禁用按钮
        self.refresh_data()
        QTimer.singleShot(1000, lambda: self.refresh_btn.setEnabled(True))  # 1秒后重新启用按钮

    def refresh_data(self):
        """刷新数据显示"""
        conn = None  # 在方法开始时初始化 conn
        try:
            # 检查数据库文件是否存在
            if not os.path.exists(self.db_path):
                self.show_error(f"数据库文件不存在: {self.db_path}\n请确保数据库文件存在并包含正确的资产数据。")
                return

            # 获取设备名称
            device_name = platform.node() or socket.gethostname()

            # 连接数据库
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 构建查询条件
            conditions = []
            params = []

            # 搜索条件
            if self.current_search:
                conditions.append("(epc LIKE ? OR description LIKE ?)")
                params.extend([f"%{self.current_search}%", f"%{self.current_search}%"])

            # 时间范围条件
            start_datetime = f"{self.start_date.getDate().toString('yyyy-MM-dd')} {self.start_time.time.toString('HH:mm:ss')}"
            end_datetime = f"{self.end_date.getDate().toString('yyyy-MM-dd')} {self.end_time.time.toString('HH:mm:ss')}"
            print(f"查询时间范围: {start_datetime} 到 {end_datetime}")  # 调试日志

            conditions.append("scan_time BETWEEN ? AND ?")
            params.extend([start_datetime, end_datetime])

            # 组合查询条件
            where_clause = " AND ".join(conditions) if conditions else "1"

            # 获取总记录数
            count_query = f"SELECT COUNT(*) FROM scan_history WHERE {where_clause}"
            print(f"计数查询: {count_query}")  # 调试日志
            print(f"参数: {params}")  # 调试日志

            cursor.execute(count_query, params)
            self.total_records = cursor.fetchone()[0]
            print(f"总记录数: {self.total_records}")  # 调试日志

            # 更新统计信息
            self.total_label.setText(f"总记录数: {self.total_records}")
            self.current_page_label.setText(f"当前页: {self.current_page}")

            # 计算分页
            offset = (self.current_page - 1) * self.page_size

            # 查询数据
            query = f"""
                SELECT id, epc, scan_time, scan_device, description 
                FROM scan_history 
                WHERE {where_clause}
                ORDER BY scan_time DESC
                LIMIT {self.page_size} OFFSET {offset}
            """
            print(f"数据查询: {query}")  # 调试日志
            print(f"参数: {params}")  # 调试日志

            cursor.execute(query, params)
            data = cursor.fetchall()
            print(f"查询到 {len(data)} 条记录")  # 调试日志

            # 显示数据
            self.table.setRowCount(len(data))
            for row, record in enumerate(data):
                self.table.setItem(row, 0, QTableWidgetItem(str(record[0])))  # ID

                # 处理EPC编号，只移除多余的0（超过12位的部分）
                epc = str(record[1])
                if len(epc) > 12:  # 如果长度超过12位
                    epc = epc[:12]  # 保留前12位
                self.table.setItem(row, 1, QTableWidgetItem(epc))  # EPC

                self.table.setItem(row, 2, QTableWidgetItem(str(record[2])))  # 扫描时间
                self.table.setItem(row, 3, QTableWidgetItem(str(record[3] or "")))  # 设备名称
                self.table.setItem(row, 4, QTableWidgetItem(str(record[4] or "")))  # 资产描述

            # 更新分页按钮状态
            self.prev_btn.setEnabled(self.current_page > 1)
            self.next_btn.setEnabled(offset + self.page_size < self.total_records)

        except sqlite3.Error as e:
            self.show_error(f"数据刷新失败: {str(e)}")
            print(f"数据库错误: {str(e)}")  # 调试日志
        except Exception as e:
            self.show_error(f"刷新数据时出错: {str(e)}")
            print(f"其他错误: {str(e)}")  # 调试日志
        finally:
            if conn:
                conn.close()

    def show_error(self, message: str):
        """显示错误信息"""
        InfoBar.error(
            title='错误',
            content=message,
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )

    def on_search_changed(self):
        """搜索条件改变时的处理"""
        self.current_search = self.search_edit.text()
        self.current_page = 1
        self.refresh_data()

    def prev_page(self):
        """显示上一页"""
        if self.current_page > 1:
            self.current_page -= 1
            self.refresh_data()

    def next_page(self):
        """显示下一页"""
        if (self.current_page * self.page_size) < self.total_records:
            self.current_page += 1
            self.refresh_data()

    def showEvent(self, event):
        """当页面显示时触发"""
        super().showEvent(event)
        self.refresh_data()  # 每次显示页面时刷新数据

    def hideEvent(self, event):
        """当页面隐藏时触发"""
        super().hideEvent(event)
        self.refresh_timer.stop()  # 停止自动刷新

    def closeEvent(self, event):
        """当窗口关闭时触发"""
        self.refresh_timer.stop()  # 确保定时器被停止
        super().closeEvent(event)

    def on_date_changed(self):
        """日期变更事件处理"""
        self.refresh_data()

    def on_time_changed(self):
        """时间变更事件处理"""
        self.refresh_data()
