import os
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QWidget, QVBoxLayout, QGroupBox
from qfluentwidgets import SubtitleLabel, PushButton, ComboBox

# noinspection PyUnresolvedReferences
from serial_handler import POWER_COMMANDS


class BlankPage(QWidget):
    """功率设置页面"""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("blankPage")

        # 初始化控件变量
        self.label_power = None  # 功率显示标签
        self.combo_power = None  # 功率选择下拉框
        self.btn_set_power = None  # 设置功率按钮

        # 初始化界面
        self.setup_ui()

    def setup_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 40, 20, 20)

        # 创建功率设置组
        power_group = QGroupBox("功率/增益设置", self)
        power_layout = QVBoxLayout()
        power_layout.setSpacing(5)
        power_layout.setContentsMargins(5, 5, 5, 5)

        # 添加功率显示标签
        self.label_power = SubtitleLabel("当前功率/增益: --", self)
        power_layout.addWidget(self.label_power)

        # 创建功率选择下拉框
        self.combo_power = ComboBox(self)
        self.combo_power.addItems(list(POWER_COMMANDS.keys()))
        self.combo_power.setMinimumHeight(30)
        power_layout.addWidget(self.combo_power)

        # 添加设置功率按钮
        self.btn_set_power = PushButton("设置发射功率", self)
        self.btn_set_power.setMinimumHeight(30)
        power_layout.addWidget(self.btn_set_power)

        power_group.setLayout(power_layout)
        layout.addWidget(power_group)

        # 添加一个弹性空间
        layout.addStretch()

        # 设置布局
        self.setLayout(layout)
