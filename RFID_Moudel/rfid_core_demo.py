#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RFID核心功能模块使用示例
演示如何使用rfid_core.py中的RFIDReader类实现基本功能
"""

import threading
import time

from rfid_core import RFIDReader


def main():
    """主函数，演示RFID核心功能的使用"""
    # 创建计数器和锁，用于统计读取到的卡片数量
    card_count = {'value': 0}
    card_lock = threading.Lock()

    # 定义卡片处理回调函数
    def card_handler(card_info):
        with card_lock:
            card_count['value'] += 1
            print(f"[{card_count['value']}] 读取到卡片: EPC={card_info['epc']}, RSSI={card_info['rssi']} dBm")

    # 创建RFID读卡器实例
    reader = RFIDReader()

    # 列出可用设备
    print("=== 可用设备列表 ===")
    devices = reader.list_devices()
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
    if not reader.connect(selected_port):
        print("连接失败")
        return

    print("连接成功!")

    # 显示菜单并处理用户选择
    while True:
        print("\n=== RFID功能菜单 ===")
        print("1. 单次读卡")
        print("2. 开始群读 (按Ctrl+C停止)")
        print("3. 设置读卡器功率")
        print("4. 获取当前功率/增益")
        print("5. 断开连接并退出")

        try:
            choice = int(input("请选择操作 (1-5): "))

            if choice == 1:
                # 单次读卡
                print("\n执行单次读卡...")
                card = reader.read_card_once()
                if card:
                    print(f"读取到卡片: EPC={card['epc']}, RSSI={card['rssi']} dBm")
                else:
                    print("未读取到卡片")

            elif choice == 2:
                # 开始群读
                print("\n开始群读模式 (按Ctrl+C停止)...")
                card_count['value'] = 0  # 重置计数器

                if reader.start_reading(card_handler):
                    try:
                        # 无限循环，直到用户按Ctrl+C
                        while True:
                            time.sleep(0.1)

                    except KeyboardInterrupt:
                        print("\n用户停止群读")
                    finally:
                        reader.stop_reading()
                        print(f"群读已停止，共读取到 {card_count['value']} 张卡片")
                else:
                    print("启动群读失败")

            elif choice == 3:
                # 设置读卡器功率
                print("\n=== 可用功率级别 ===")
                power_levels = [
                    "12.5 dBm (0.6m)",
                    "14 dBm (0.8m)",
                    "15.5 dBm (0.9m)",
                    "17 dBm (1m)",
                    "18.5 dBm (1.15m)",
                    "20 dBm (2m)"
                ]

                for i, level in enumerate(power_levels):
                    print(f"{i + 1}. {level}")

                try:
                    p_choice = int(input("请选择功率级别 (1-6): "))
                    if p_choice < 1 or p_choice > len(power_levels):
                        print("无效的选择")
                        continue

                    selected_power = power_levels[p_choice - 1]
                    if reader.set_power(selected_power):
                        print(f"功率设置成功: {selected_power}")
                    else:
                        print("功率设置失败")

                except ValueError:
                    print("请输入有效数字")

            elif choice == 4:
                # 获取当前功率/增益
                gain = reader.get_current_gain()
                if gain is not None:
                    print(f"当前读卡器功率/增益: {gain} dBm")
                else:
                    print("获取功率/增益失败")

            elif choice == 5:
                # 断开连接并退出
                print("\n正在断开连接...")
                reader.disconnect()
                print("已断开连接，程序退出")
                break

            else:
                print("无效的选择，请输入1-5之间的数字")

        except ValueError:
            print("请输入有效数字")
        except KeyboardInterrupt:
            print("\n\n用户中断程序")
            reader.disconnect()
            break
        except Exception as e:
            print(f"发生错误: {str(e)}")


if __name__ == "__main__":
    print("=== RFID核心功能演示程序 ===")
    try:
        main()
    except Exception as e:
        print(f"程序异常: {str(e)}")
    print("程序已退出")
