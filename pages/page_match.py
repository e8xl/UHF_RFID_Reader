import os
import sqlite3
import sys
from typing import Optional, Any

from PySide6.QtCore import QDateTime
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from qfluentwidgets import LineEdit, PushButton, TextEdit


class MainWindow:
    """用于类型提示的主窗口类存根"""
    ser: Any
    def start_card_matching(self, number: str) -> None: ...
    def stop_reading(self) -> None: ...


class MatchPage(QWidget):
    """
    卡号匹配页面
    用于输入数字与群读获取的EPC进行匹配
    """

    def __init__(self, parent: Optional[MainWindow] = None):
        super().__init__(parent)
        self.parent: Optional[MainWindow] = parent

        # 设置对象名称
        self.setObjectName("matchPage")

        # 初始化实例特性
        self.number_input: Optional[LineEdit] = None
        self.btn_match: Optional[PushButton] = None
        self.btn_stop: Optional[PushButton] = None
        self.btn_clear: Optional[PushButton] = None
        self.result_display: Optional[TextEdit] = None
        self.match_count: int = 0
        self.asset_data: dict[str, dict[str, Any]] = {}

        # 获取数据库文件的绝对路径
        self.db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'asset_report.db')

        # 先初始化界面，这样result_display就会被创建
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
                error_msg = f"数据库文件不存在: {self.db_path}\n请确保数据库文件存在并包含正确的资产数据。"
                if self.result_display:
                    self.append_result(error_msg)
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
                    epc_clean = ''.join(filter(str.isdigit, epc_str))

                    # 确保EPC至少有"46"前缀
                    if not epc_clean.startswith('46'):
                        epc_clean = '46' + epc_clean

                    self.asset_data[epc_clean] = row_dict
                    print(f"加载EPC: {epc_clean}")

            self.append_result(f"已从数据库加载 {len(self.asset_data)} 条资产记录")
            print(f"加载的所有资产: {list(self.asset_data.keys())}")

        except sqlite3.Error as e:
            error_msg = f"数据库读取错误: {str(e)}\n"
            error_msg += f"数据库路径: {self.db_path}\n"
            error_msg += f"当前工作目录: {os.getcwd()}\n"
            error_msg += f"Python搜索路径: {sys.path}"

            if self.result_display:
                self.append_result(error_msg)
            print(error_msg)
        except Exception as e:
            error_msg = f"加载资产数据时出错: {str(e)}\n"
            error_msg += f"错误类型: {type(e)}\n"
            error_msg += f"数据库路径: {self.db_path}"

            if self.result_display:
                self.append_result(error_msg)
            print(error_msg)
        finally:
            if conn:
                conn.close()

    def match_with_database(self, epc):
        """
        将EPC与数据库记录进行匹配
        参数:
            epc: 读取到的EPC号码
        返回:
            匹配到的资产信息或None
        """
        try:
            # 1. 标准化读取到的EPC
            # 移除空格并转换为连续字符串
            epc_clean = ''.join(epc.split())

            # 2. 如果EPC不是以'46'开头，添加'46'前缀
            if not epc_clean.startswith('46'):
                epc_clean = '46' + epc_clean

            print(f"标准化后的EPC: {epc_clean}")

            # 3. 获取用户输入的目标数字
            target_number = self.number_input.text().strip()
            if not target_number:
                return None

            print(f"目标数字: {target_number}")
            print(f"当前数据库中的资产: {list(self.asset_data.keys())}")

            # 4. 在数据库中查找匹配
            for db_epc, asset_info in self.asset_data.items():
                # 标准化数据库中的EPC
                db_epc_clean = ''.join(filter(str.isdigit, str(db_epc)))
                print(f"比较: EPC={epc_clean} vs DB_EPC={db_epc_clean}")

                # 如果标准化后的EPC包含目标数字
                if target_number in db_epc_clean:
                    print(f"在数据库中找到匹配记录: {db_epc_clean}")
                    return asset_info

            print(f"未找到匹配: EPC={epc_clean}")
            return None

        except Exception as e:
            self.append_result(f"匹配过程出错: {str(e)}")
            print(f"匹配过程出错: {str(e)}")
            return None

    def init_ui(self):
        """初始化用户界面"""
        # 创建主布局并设置边距
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 70, 20, 20)  # 左、上、右、下的边距
        layout.setSpacing(15)  # 组件之间的间距

        # 创建输入区域
        input_layout = QHBoxLayout()
        input_layout.setSpacing(10)

        label = QLabel("卡号：", self)
        label.setObjectName("inputLabel")

        self.number_input = LineEdit(self)
        self.number_input.setObjectName("numberInput")
        self.number_input.setPlaceholderText("请输入需要匹配的卡号（至少10-12位数字）")
        self.number_input.setMinimumWidth(300)

        input_layout.addWidget(label)
        input_layout.addWidget(self.number_input)
        input_layout.addStretch()

        # 创建按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.btn_match = PushButton("开始匹配", self)
        self.btn_match.setObjectName("matchButton")
        self.btn_stop = PushButton("结束匹配", self)
        self.btn_stop.setObjectName("stopButton")
        self.btn_stop.setEnabled(False)
        self.btn_clear = PushButton("清除记录", self)
        self.btn_clear.setObjectName("clearButton")

        button_layout.addWidget(self.btn_match)
        button_layout.addWidget(self.btn_stop)
        button_layout.addWidget(self.btn_clear)
        button_layout.addStretch()

        # 创建结果显示区域
        result_label = QLabel("匹配结果：", self)
        result_label.setObjectName("resultLabel")

        self.result_display = TextEdit(self)
        self.result_display.setObjectName("resultDisplay")
        self.result_display.setReadOnly(True)
        self.result_display.setMinimumHeight(400)

        # 添加所有组件到主布局
        layout.addLayout(input_layout)
        layout.addLayout(button_layout)
        layout.addWidget(result_label)
        layout.addWidget(self.result_display)

        # 连接信号和槽
        self.btn_match.clicked.connect(self.start_matching)
        self.btn_stop.clicked.connect(self.stop_matching)
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

    def start_matching(self):
        """开始匹配过程"""
        # 首先检查设备连接状态
        if not self.parent or not hasattr(self.parent, 'ser') or not self.parent.ser:
            self.append_result("错误：请先连接设备后再开始匹配！")
            return

        input_number = self.number_input.text().strip()

        # 验证输入
        if not input_number.isdigit():
            self.append_result("错误：请输入纯数字！")
            return

        if len(input_number) < 10:
            self.append_result("错误：输入数字长度不足，请至少输入10位数字！")
            return

        self.append_result(f"开始匹配目标数字: {input_number}")

        # 更新按钮状态
        self.btn_match.setEnabled(False)
        self.btn_stop.setEnabled(True)

        # 通知主窗口开始匹配
        if hasattr(self.parent, 'start_card_matching'):
            self.parent.start_card_matching(input_number)

    def stop_matching(self):
        """停止匹配过程"""
        # 更新按钮状态
        self.btn_match.setEnabled(True)
        self.btn_stop.setEnabled(False)

        # 通知主窗口停止群读
        if hasattr(self.parent, 'stop_reading'):
            self.parent.stop_reading()

    def reset_match_state(self):
        """重置匹配状态和按钮"""
        self.btn_match.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.match_count = 0  # 重置计数器

    def append_result(self, message):
        """添加匹配结果到显示区域"""
        if not self.result_display:
            return

        # 如果是匹配成功的消息，增加计数并添加资产信息
        if "找到匹配" in message:
            self.match_count += 1
            timestamp = QDateTime.currentDateTime().toString("HH:mm:ss")

            # 从消息中提取EPC
            try:
                epc_start = message.find("完整EPC: ") + 9
                epc_end = message.find("\n", epc_start)
                epc = message[epc_start:epc_end].strip()

                # 查找匹配的资产信息
                asset_info = self.match_with_database(epc)
                if asset_info:
                    # 按固定顺序显示字段，并添加中文说明
                    fields_order = [
                        ('Class', '资产类别'),
                        ('Asset', 'EPC编号'),
                        ('SNo.', '序列号'),
                        ('asset no', '资产编号'),
                        ('Cost ctr', '成本中心'),
                        ('ActTyp', '资产类型'),
                        ('Asset description', '资产描述'),
                        ('Asset main no. text', '资产主编号说明'),
                        ('Orig. asset', '原始资产'),
                        ('Serial no.', '序列号'),
                        ('Inventory number', '库存编号'),
                        ('Curr.', '货币'),
                        ('First acq.', '首次采购'),
                        ('Acq.val.FYE', '年末采购值'),
                        ('Netbk.val FYE', '年末账面净值'),
                        ('Ord.dep. FYE', '年末普通折旧'),
                        ('Deact.Date', '停用日期')
                    ]

                    # 格式化资产信息
                    asset_details = []
                    for field, cn_name in fields_order:
                        value = asset_info.get(field)
                        if value is not None:  # 检查是否为None
                            # 将所有值转换为字符串
                            value_str = str(value).rstrip('0').rstrip('.') if isinstance(value, float) else str(value)
                            if value_str:  # 只显示非空值
                                asset_details.append(f"{cn_name}: {value_str}")

                    message = (
                            f"[{timestamp}] 匹配次数.{self.match_count}：\n"
                            f"信号强度: {asset_info.get('rssi', '')} dBm\n"
                            f"资产信息：\n" + "\n".join(asset_details) + "\n"
                                                                        f"------------------------"
                    )
                else:
                    message = (
                        f"[{timestamp}] 匹配次数.{self.match_count}：\n"
                        f"完整EPC: {epc}\n"
                        f"警告：未在数据库中找到对应资产信息\n"
                        f"------------------------"
                    )
            except Exception as e:
                self.result_display.append(f"处理资产信息时出错: {str(e)}")

        self.result_display.append(message)

    def clear_results(self):
        """清除结果显示区域和计数器"""
        self.result_display.clear()
        self.match_count = 0  # 重置计数器
