import os
import sqlite3
import platform
import socket
from datetime import datetime
from typing import Optional, Dict, Any, Set

from PySide6.QtCore import QDateTime
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QAbstractItemView, QHeaderView, QTableWidgetItem, QSizePolicy
)
from qfluentwidgets import (
    PushButton, TextEdit, TableWidget, TableItemDelegate
)


class SearchPage(QWidget):
    """
    群体搜索页面
    用于群读获取的EPC进行数据库匹配
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.parent = parent

        # 设置对象名称
        self.setObjectName("searchPage")

        # 初始化实例特性
        self.btn_search: Optional[PushButton] = None
        self.btn_stop: Optional[PushButton] = None
        self.btn_clear: Optional[PushButton] = None
        self.result_table: Optional[TableWidget] = None
        self.log_display: Optional[TextEdit] = None
        self.asset_data: Dict[str, Dict[str, Any]] = {}
        self.found_epcs: Set[str] = set()  # 用于记录已找到的EPC，避免重复显示

        # 获取数据库文件的绝对路径
        self.db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'asset_report.db')

        # 先初始化界面
        self.init_ui()

        # 然后加载数据库数据
        self.load_asset_data()

    def load_asset_data(self):
        """从数据库加载资产数据到内存"""
        conn = None
        try:
            print(f"尝试连接数据库: {self.db_path}")
            
            # 检查数据库文件是否存在
            if not os.path.exists(self.db_path):
                error_msg = f"数据库文件不存在: {self.db_path}"
                self.append_log(error_msg)
                print(error_msg)
                return

            # 使用绝对路径连接数据库
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 获取表结构信息
            cursor.execute("PRAGMA table_info(master_data_table)")
            columns = [column[1] for column in cursor.fetchall()]

            # 读取所有资产数据
            cursor.execute("SELECT * FROM master_data_table")
            rows = cursor.fetchall()

            # 将数据存储为字典，以EPC为键
            for row in rows:
                row_dict = dict(zip(columns, row))
                epc = row_dict.get('Asset')
                if epc is not None:
                    # 直接将EPC转换为字符串，保留所有数字
                    epc_str = str(epc)
                    # 如果是科学计数法，转换为普通数字
                    if 'e' in epc_str.lower():
                        epc_str = f"{float(epc):.0f}"
                    # 移除所有非数字字符
                    epc_clean = ''.join(c for c in epc_str if c.isdigit())

                    # 确保EPC至少有"46"前缀
                    if not epc_clean.startswith('46'):
                        epc_clean = '46' + epc_clean

                    self.asset_data[epc_clean] = row_dict

            self.append_log(f"已从数据库加载 {len(self.asset_data)} 条资产记录")

        except sqlite3.Error as e:
            if self.log_display:
                self.append_log(f"数据库读取错误: {str(e)}")
        finally:
            if conn is not None:
                conn.close()

    def init_ui(self):
        """初始化用户界面"""
        # 创建主布局并设置边距
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 70, 20, 20)  # 左、上、右、下的边距
        layout.setSpacing(15)  # 组件之间的间距

        # 创建按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.btn_search = PushButton("开始搜索", self)
        self.btn_search.setObjectName("searchButton")
        self.btn_stop = PushButton("结束搜索", self)
        self.btn_stop.setObjectName("stopButton")
        self.btn_stop.setEnabled(False)
        self.btn_clear = PushButton("清除记录", self)
        self.btn_clear.setObjectName("clearButton")

        button_layout.addWidget(self.btn_search)
        button_layout.addWidget(self.btn_stop)
        button_layout.addWidget(self.btn_clear)
        button_layout.addStretch()

        # 创建表格显示区域
        table_group = QGroupBox("匹配结果", self)
        table_layout = QVBoxLayout()

        self.result_table = TableWidget(self)
        self.result_table.setColumnCount(5)  # 减少到5列
        self.result_table.setHorizontalHeaderLabels([
            "序号", "EPC编号", "资产描述", "成本中心", "匹配时间"
        ])
        self.result_table.setItemDelegate(TableItemDelegate(self.result_table))
        self.result_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.result_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.result_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.result_table.horizontalHeader().setStretchLastSection(False)

        # 设置每列的宽度配置
        column_configs = {
            0: {"width": 15, "min_width": 15, "mode": QHeaderView.ResizeMode.Fixed},  # 序号列（两位数字）
            1: {"width": 80, "min_width": 80, "mode": QHeaderView.ResizeMode.Fixed},  # EPC编号
            2: {"width": None, "min_width": 200, "mode": QHeaderView.ResizeMode.Stretch},  # 资产描述
            3: {"width": 120, "min_width": 120, "mode": QHeaderView.ResizeMode.Fixed},  # 成本中心
            4: {"width": 100, "min_width": 100, "mode": QHeaderView.ResizeMode.Fixed}  # 匹配时间
        }

        # 设置列宽和调整模式
        header = self.result_table.horizontalHeader()
        for col, config in column_configs.items():
            # 设置最小宽度
            header.setMinimumSectionSize(config["min_width"])
            # 设置初始宽度（如果指定了的话）
            if config["width"]:
                self.result_table.setColumnWidth(col, config["width"])
            # 最后设置调整模式
            header.setSectionResizeMode(col, config["mode"])

        # 强制应用序号列的宽度
        self.result_table.setColumnWidth(0,15)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)

        # 禁用水平滚动条
        self.result_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # 设置表格的大小策略
        self.result_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.result_table.setMinimumHeight(300)
        self.result_table.verticalHeader().setVisible(False)

        table_layout.addWidget(self.result_table)
        table_group.setLayout(table_layout)

        # 创建日志显示区域
        log_group = QGroupBox("操作日志", self)
        log_layout = QVBoxLayout()

        self.log_display = TextEdit(self)
        self.log_display.setObjectName("logDisplay")
        self.log_display.setReadOnly(True)
        self.log_display.setMinimumHeight(150)

        log_layout.addWidget(self.log_display)
        log_group.setLayout(log_layout)

        # 添加所有组件到主布局
        layout.addLayout(button_layout)
        layout.addWidget(table_group)
        layout.addWidget(log_group)

        # 连接信号和槽
        self.btn_search.clicked.connect(self.start_searching)
        self.btn_stop.clicked.connect(self.stop_searching)
        self.btn_clear.clicked.connect(self.clear_results)

        # 设置样式
        self.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: black;
            }
            TextEdit {
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                padding: 8px;
            }
        """)

    def start_searching(self):
        """开始搜索过程"""
        # 首先检查设备连接状态
        if not self.parent or not hasattr(self.parent, 'ser') or not getattr(self.parent, 'ser', None):
            self.append_log("错误：请先连接设备后再开始搜索！")
            return

        self.append_log("开始群体搜索...")
        self.append_log(f"当前数据库中共有 {len(self.asset_data)} 条记录")
        self.append_log("等待读取RFID标签...")

        # 更新按钮状态
        self.btn_search.setEnabled(False)
        self.btn_stop.setEnabled(True)

        # 通知主窗口开始群读
        if hasattr(self.parent, 'read_cards'):
            self.parent.read_cards()

    def stop_searching(self):
        """停止搜索过程"""
        # 更新按钮状态
        self.btn_search.setEnabled(True)
        self.btn_stop.setEnabled(False)

        # 通知主窗口停止群读
        if hasattr(self.parent, 'stop_reading'):
            self.parent.stop_reading()

        self.append_log("搜索已停止")

    def clear_results(self):
        """清除结果显示区域"""
        self.result_table.setRowCount(0)
        self.log_display.clear()
        self.found_epcs.clear()

    def append_log(self, message):
        """添加日志消息"""
        if self.log_display:
            timestamp = QDateTime.currentDateTime().toString("HH:mm:ss")
            self.log_display.append(f"[{timestamp}] {message}")

    def save_scan_record(self, epc, asset_info):
        """
        保存扫描记录到scan_history表
        参数:
            epc: EPC编号
            asset_info: 资产信息字典
        """
        try:
            # 获取当前时间
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 获取设备名称
            device_name = platform.node() or socket.gethostname()

            # 连接数据库
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 准备插入数据
            cursor.execute("""
                INSERT INTO scan_history (epc, scan_time, description, scan_device)
                VALUES (?, ?, ?, ?)
            """, (epc, current_time, asset_info.get('Asset description', ''), device_name))

            # 提交事务
            conn.commit()
            self.append_log(f"扫描记录已保存 - EPC: {epc}, 时间: {current_time}, 设备: {device_name}")

        except sqlite3.Error as e:
            self.append_log(f"保存扫描记录时出错: {str(e)}")
        finally:
            if conn:
                conn.close()

    def match_with_database(self, card_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        将EPC与数据库记录进行匹配
        参数:
            card_info: 包含卡片信息的字典
        返回:
            匹配到的资产信息或None
        """
        try:
            # 获取并清理EPC
            epc = card_info['epc']
            epc_clean = ''.join(c for c in epc.replace(" ", "") if c.isdigit())

            # # 如果EPC不是以'46'开头，添加'46'前缀
            # if not epc_clean.startswith('46'):
            #     epc_clean = '46' + epc_clean

            # 添加调试日志
            self.append_log(f"读取到新标签 - EPC: {epc}")
            self.append_log(f"清理后的EPC: {epc_clean}")

            # 检查是否已经找到过这个EPC
            if epc_clean in self.found_epcs:
                self.append_log(f"该标签已扫描过，跳过")
                return None

            # 在数据库中查找匹配
            # 首先尝试完全匹配
            if epc_clean in self.asset_data:
                self.found_epcs.add(epc_clean)
                asset_info = self.asset_data[epc_clean]
                asset_info['rssi'] = card_info['rssi']
                self.append_log(f"在数据库中找到完全匹配！")
                # 保存扫描记录
                self.save_scan_record(epc_clean, asset_info)
                return asset_info

            # 如果完全匹配失败，尝试前缀匹配
            for db_epc, asset_info in self.asset_data.items():
                # 如果数据库中的EPC是读取到的EPC的前缀
                if epc_clean.startswith(db_epc):
                    self.found_epcs.add(epc_clean)
                    asset_info['rssi'] = card_info['rssi']
                    self.append_log(f"在数据库中找到前缀匹配！数据库EPC: {db_epc}")
                    # 保存扫描记录
                    self.save_scan_record(epc_clean, asset_info)
                    return asset_info
                # 如果读取到的EPC是数据库中EPC的前缀
                elif db_epc.startswith(epc_clean):
                    self.found_epcs.add(epc_clean)
                    asset_info['rssi'] = card_info['rssi']
                    self.append_log(f"在数据库中找到前缀匹配！数据库EPC: {db_epc}")
                    # 保存扫描记录
                    self.save_scan_record(epc_clean, asset_info)
                    return asset_info

            self.append_log(f"未在数据库中找到匹配记录")
            return None

        except Exception as e:
            self.append_log(f"匹配过程出错: {str(e)}")
            return None

    def add_match_result(self, card_info: Dict[str, Any], asset_info: Dict[str, Any]) -> None:
        """
        将匹配结果添加到表格中
        参数:
            card_info: 卡片信息字典
            asset_info: 资产信息字典
        """
        if not self.result_table or not asset_info:
            return

        try:
            # 添加新记录
            row = self.result_table.rowCount()
            self.result_table.insertRow(row)

            # 获取当前时间
            current_time = QDateTime.currentDateTime().toString("HH:mm:ss")

            # 设置各列数据
            self.result_table.setItem(row, 0, QTableWidgetItem(f"{row + 1:02d}"))  # 序号
            self.result_table.setItem(row, 1, QTableWidgetItem(str(asset_info.get('Asset', ''))))  # EPC编号
            self.result_table.setItem(row, 2, QTableWidgetItem(str(asset_info.get('Asset description', ''))))  # 资产描述
            self.result_table.setItem(row, 3, QTableWidgetItem(str(asset_info.get('Cost ctr', ''))))  # 成本中心
            self.result_table.setItem(row, 4, QTableWidgetItem(current_time))  # 匹配时间

            # 滚动到新行
            self.result_table.scrollToBottom()

            # 添加日志
            self.append_log(
                f"找到新设备 - EPC: {asset_info.get('Asset', '')}, 描述: {asset_info.get('Asset description', '')}")

        except Exception as e:
            self.append_log(f"添加匹配结果时出错: {str(e)}")
