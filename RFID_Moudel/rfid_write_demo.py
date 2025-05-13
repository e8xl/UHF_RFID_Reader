#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RFID写入功能演示程序
展示如何使用rfid_core.py模块进行RFID标签的写入操作
"""

from rfid_core import RFIDReader


def main():
    """主函数"""
    print("=== RFID写入功能演示 ===")

    # 创建RFID读卡器实例
    reader = RFIDReader()

    # 列出可用设备
    print("\n可用设备列表:")
    devices = reader.list_devices()
    if not devices:
        print("未检测到任何设备")
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

    try:
        while True:
            print("\n=== RFID写入菜单 ===")
            print("1. 读取标签")
            print("2. 写入数据到用户区")
            print("3. 写入EPC")
            print("4. 读取EPC区")
            print("5. 读取用户区")
            print("6. 退出")

            try:
                choice = int(input("\n请选择操作 (1-6): "))

                if choice == 1:
                    # 读取标签
                    print("\n正在读取标签...")
                    card = reader.read_card_once()
                    if card:
                        print(f"读取成功:")
                        print(f"  EPC: {card['epc']}")
                        print(f"  PC: {card['pc']}")
                        print(f"  CRC: {card['crc']}")
                        print(f"  RSSI: {card['rssi']} dBm")

                        # 将当前EPC设置为SELECT参数
                        set_as_select = input("\n是否将此EPC设置为SELECT目标? (y/n): ").lower().strip()
                        if set_as_select == 'y':
                            if reader.set_select_params(card['epc']):
                                print("已设置为SELECT目标")
                            else:
                                print("设置SELECT目标失败")
                    else:
                        print("读取失败，未找到标签")

                elif choice == 2:
                    # 写入数据到用户区
                    data = input("\n请输入要写入的16进制数据 (如: 01020304): ").strip()
                    if not data:
                        print("数据不能为空")
                        continue

                    print(f"\n正在写入数据: {data}")
                    if reader.write_card(data):
                        print("写入成功!")
                    else:
                        print("写入失败")

                elif choice == 3:
                    # 写入EPC
                    new_epc = input("\n请输入要写入的EPC (24个16进制字符): ").strip()
                    if not new_epc:
                        print("EPC不能为空")
                        continue

                    # 如果需要，也可以提供访问密码
                    access_pwd = input("请输入访问密码 (默认为00000000): ").strip()
                    if not access_pwd:
                        access_pwd = "00000000"

                    print(f"\n正在写入EPC: {new_epc}")
                    if reader.write_epc(new_epc, access_pwd):
                        print("EPC写入成功!")
                    else:
                        print("EPC写入失败")

                elif choice == 4:
                    # 读取EPC区
                    print("\n正在读取EPC区...")
                    epc_data = reader.read_tag_memory(
                        membank=0x01,  # EPC区
                        start_addr=0x02,  # EPC起始位置
                        length=0x06  # 6个字 (12字节)
                    )

                    if epc_data:
                        print(f"EPC区数据: {epc_data}")
                    else:
                        print("读取EPC区失败")

                elif choice == 5:
                    # 读取用户区
                    print("\n正在读取用户区...")
                    access_pwd = input("请输入访问密码 (默认为00000000): ").strip()
                    if not access_pwd:
                        access_pwd = "00000000"

                    # 读取指定长度的用户区数据
                    length = input("请输入要读取的字节数量 (默认为4字节): ").strip()
                    try:
                        length = int(length) if length else 4
                        # 将字节数转换为字数 (word count)
                        word_count = (length + 1) // 2
                    except ValueError:
                        print("无效的长度，使用默认值4字节")
                        word_count = 2

                    user_data = reader.read_tag_memory(
                        access_password=access_pwd,
                        membank=0x03,  # 用户区
                        start_addr=0x00,  # 起始位置
                        length=word_count  # 字数
                    )

                    if user_data:
                        print(f"用户区数据: {user_data}")
                    else:
                        print("读取用户区失败")

                elif choice == 6:
                    # 退出
                    break

                else:
                    print("无效的选择，请输入1-6之间的数字")

            except ValueError:
                print("请输入有效数字")
            except Exception as e:
                print(f"操作出错: {str(e)}")

            # 每次操作后暂停，让用户有时间查看结果
            input("\n按回车键继续...")

    except KeyboardInterrupt:
        print("\n\n用户中断程序")
    finally:
        # 断开连接
        print("\n正在断开设备连接...")
        reader.disconnect()
        print("已断开连接，程序退出")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"程序异常: {str(e)}")
