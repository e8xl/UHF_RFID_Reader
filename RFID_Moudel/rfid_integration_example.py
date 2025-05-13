#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RFID核心功能模块集成示例
展示如何将rfid_core模块集成到其他应用程序中
"""

import threading
import time

from rfid_core import RFIDReader


class SimpleRFIDApplication:
    """
    简单的RFID应用程序示例类
    展示如何在更大的应用程序中集成RFID功能
    """

    def __init__(self):
        """初始化应用程序"""
        # 创建RFID读卡器实例并设置日志回调
        self.reader = RFIDReader(log_callback=self.log_handler)
        self.running = False
        self.inventory = {}  # 用于存储已读取卡片的字典
        self.inventory_lock = threading.Lock()  # 用于保护inventory的线程锁

    def log_handler(self, message):
        """处理来自RFID模块的日志消息"""
        print(f"[RFID日志] {message}")

    def card_handler(self, card_info):
        """处理读取到的卡片信息"""
        epc = card_info['epc']
        rssi = card_info['rssi']

        with self.inventory_lock:
            if epc in self.inventory:
                # 更新现有卡片的信息
                self.inventory[epc]['count'] += 1
                self.inventory[epc]['last_seen'] = time.time()
                self.inventory[epc]['rssi'] = rssi
            else:
                # 添加新卡片
                self.inventory[epc] = {
                    'first_seen': time.time(),
                    'last_seen': time.time(),
                    'count': 1,
                    'rssi': rssi,
                    'pc': card_info['pc'],
                    'crc': card_info['crc']
                }
                # 打印新发现的卡片
                print(f"发现新卡片: EPC={epc}, RSSI={rssi} dBm")

    def connect_to_device(self, port=None):
        """连接到RFID设备"""
        if port is None:
            # 自动选择第一个可用设备
            devices = self.reader.list_devices()
            if not devices:
                print("未检测到任何COM端口设备")
                return False
            port = devices[0][0]
            print(f"自动选择设备: {port}")

        return self.reader.connect(port)

    def start_monitoring(self):
        """开始监控RFID标签"""
        if not self.reader.is_connected():
            print("设备未连接，无法开始监控")
            return False

        self.running = True
        # 启动监控线程
        self.monitor_thread = threading.Thread(target=self._monitor_thread)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

        # 开始读卡
        return self.reader.start_reading(self.card_handler)

    def _monitor_thread(self):
        """监控线程函数，定期打印统计信息"""
        last_count = 0

        while self.running:
            time.sleep(5)  # 每5秒报告一次

            with self.inventory_lock:
                current_count = sum(item['count'] for item in self.inventory.values())
                new_count = current_count - last_count

                print(f"\n--- RFID 监控状态 ---")
                print(f"总卡片数: {len(self.inventory)}")
                print(f"总读取次数: {current_count} (新增: {new_count})")
                print(f"------------------------")

                last_count = current_count

    def stop_monitoring(self):
        """停止监控RFID标签"""
        self.running = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1.0)

        return self.reader.stop_reading()

    def get_inventory_report(self):
        """获取库存报告"""
        with self.inventory_lock:
            report = []
            for epc, data in self.inventory.items():
                report.append({
                    'epc': epc,
                    'read_count': data['count'],
                    'first_seen': time.strftime('%H:%M:%S', time.localtime(data['first_seen'])),
                    'last_seen': time.strftime('%H:%M:%S', time.localtime(data['last_seen'])),
                    'rssi': data['rssi']
                })

            # 按读取次数排序
            report.sort(key=lambda x: x['read_count'], reverse=True)
            return report

    def disconnect(self):
        """断开连接并清理资源"""
        if self.running:
            self.stop_monitoring()

        return self.reader.disconnect()


# 简单的示例程序
def run_demo():
    """运行演示程序"""
    app = SimpleRFIDApplication()

    # 列出可用设备
    print("=== 可用设备列表 ===")
    devices = app.reader.list_devices()
    if not devices:
        print("未检测到任何COM端口设备")
        return

    for i, (port, desc) in enumerate(devices):
        print(f"{i + 1}. {port}: {desc}")

    # 让用户选择设备
    try:
        choice = int(input("\n请选择要连接的设备编号 (1-{}): ".format(len(devices))))
        if choice < 1 or choice > len(devices):
            print("无效的选择")
            return

        selected_port = devices[choice - 1][0]
    except ValueError:
        print("请输入有效数字")
        return

    # 连接设备
    print(f"\n正在连接到 {selected_port}...")
    if not app.connect_to_device(selected_port):
        print("连接失败")
        return

    print("连接成功!")

    # 设置功率
    print("\n设置读卡器功率...")
    app.reader.set_power("17 dBm (1m)")

    # 开始监控
    print("\n开始监控RFID标签 (运行30秒)...")
    if not app.start_monitoring():
        print("启动监控失败")
        app.disconnect()
        return

    try:
        # 运行一段时间
        for i in range(30):
            print(f"\r监控中... {30 - i}秒后结束", end="")
            time.sleep(1)
        print("\n\n监控完成!")
    except KeyboardInterrupt:
        print("\n\n用户中断监控")

    # 停止监控
    app.stop_monitoring()

    # 打印库存报告
    print("\n=== RFID 标签库存报告 ===")
    report = app.get_inventory_report()

    if not report:
        print("未读取到任何标签")
    else:
        print(f"{'EPC':<30} {'读取次数':<10} {'首次读取':<10} {'最后读取':<10} {'信号强度':<10}")
        print("-" * 75)
        for item in report:
            print(
                f"{item['epc']:<30} {item['read_count']:<10} {item['first_seen']:<10} {item['last_seen']:<10} {item['rssi']:<10}")

    # 断开连接
    app.disconnect()
    print("\n已断开连接")


if __name__ == "__main__":
    print("=== RFID核心模块集成示例 ===")
    try:
        run_demo()
    except Exception as e:
        print(f"程序异常: {str(e)}")
    print("程序已退出")
