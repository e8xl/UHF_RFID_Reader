#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RFID核心功能模块
提供设备连接和群读功能的独立调用接口

这个模块从RFID_AssetManager项目中提取核心功能,
允许在没有GUI的情况下使用RFID读卡器的基本功能。

功能:
    - 设备连接与断开
    - 获取设备列表
    - 单次读卡
    - 连续群读
    - 设置发射功率
    - Select模式操作
"""

import threading
import time
from typing import Dict, List, Tuple, Callable, Optional

import serial
import serial.tools.list_ports

# 从serial_handler.py提取的功能配置常量
POWER_COMMANDS = {
    "12.5 dBm (0.6m)": bytearray([0xBB, 0x00, 0xB6, 0x00, 0x02, 0x04, 0xE2, 0x9E, 0x7E]),
    "14 dBm (0.8m)": bytearray([0xBB, 0x00, 0xB6, 0x00, 0x02, 0x05, 0x78, 0x35, 0x7E]),
    "15.5 dBm (0.9m)": bytearray([0xBB, 0x00, 0xB6, 0x00, 0x02, 0x06, 0x0E, 0xCC, 0x7E]),
    "17 dBm (1m)": bytearray([0xBB, 0x00, 0xB6, 0x00, 0x02, 0x06, 0xA4, 0x62, 0x7E]),
    "18.5 dBm (1.15m)": bytearray([0xBB, 0x00, 0xB6, 0x00, 0x02, 0x07, 0x3A, 0xF9, 0x7E]),
    "20 dBm (2m)": bytearray([0xBB, 0x00, 0xB6, 0x00, 0x02, 0x07, 0xD0, 0x8F, 0x7E]),
}

SUCCESS_RESPONSE = bytearray([0xBB, 0x01, 0xB6, 0x00, 0x01, 0x00, 0xB8, 0x7E])


class RFIDDeviceError(Exception):
    """RFID设备操作异常类"""
    pass


class RFIDReader:
    """RFID读卡器操作类,提供设备连接和读写操作的核心功能"""

    def __init__(self, log_callback: Optional[Callable[[str], None]] = None):
        """
        初始化RFID读卡器
        
        参数:
            log_callback: 日志回调函数,用于输出日志信息
        """
        self.ser = None  # 串口对象
        self.log_callback = log_callback or (lambda msg: print(f"[RFID] {msg}"))
        self.group_read_active = False  # 群读状态
        self.read_thread = None  # 读卡线程
        self.current_power = None  # 当前功率
        self.gain = None  # 当前增益
        self.select_mode = 0x01  # 默认不使用Select
        self.select_param = None  # Select参数

    def log(self, message: str) -> None:
        """输出日志信息"""
        if self.log_callback:
            self.log_callback(message)

    @staticmethod
    def list_devices() -> List[Tuple[str, str]]:
        """
        列出系统中所有可用的COM端口
        返回:
            包含(端口名, 描述)元组的列表
        """
        ports = serial.tools.list_ports.comports()
        return [(port.device, port.description) for port in ports]

    def connect(self, port: str, baudrate: int = 115200, timeout: int = 1) -> bool:
        """
        连接到指定的串口设备
        
        参数:
            port: 串口端口名
            baudrate: 波特率,默认115200
            timeout: 超时时间,默认1秒
            
        返回:
            连接是否成功
        """
        # 检查端口是否可用
        available_ports = self.list_devices()
        available_port_names = [p[0] for p in available_ports]

        if port not in available_port_names:
            self.log(f"错误: 未识别到串口设备 {port}")
            return False

        # 断开现有连接
        self.disconnect()

        # 尝试连接
        try:
            self.ser = serial.Serial(port, baudrate, timeout=timeout)
            self.last_port = port  # 保存当前连接的端口名
            self.log(f"成功连接到 {port}")

            # 等待设备稳定
            time.sleep(0.5)

            # 连接成功后获取当前增益
            try:
                self.get_current_gain()
            except Exception as e:
                self.log(f"获取增益失败，但不影响设备连接: {str(e)}")

            return True
        except (serial.SerialException, IOError) as e:
            self.log(f"错误: {port} 连接失败，{str(e)}")
            self.ser = None
            return False

    def disconnect(self) -> bool:
        """
        断开当前连接的设备
        
        返回:
            操作是否成功
        """
        if not self.ser:
            return True  # 已经是断开状态

        success = True

        # 如果正在群读,先停止群读
        if self.group_read_active:
            self.stop_reading()

        # 关闭串口连接
        try:
            self.ser.close()
        except (serial.SerialException, IOError) as e:
            self.log(f"关闭串口时出现错误: {str(e)}")
            success = False

        self.ser = None
        self.log("设备已断开连接")
        return success

    def is_connected(self) -> bool:
        """
        检查设备是否已连接
        
        返回:
            设备是否已连接
        """
        return self.ser is not None and self.ser.is_open

    def send_command(self, command: bytearray) -> bytearray:
        """
        向设备发送命令并读取响应
        
        参数:
            command: 要发送的命令字节序列
            
        返回:
            设备的响应数据
            
        异常:
            RFIDDeviceError: 设备操作错误
        """
        if not self.is_connected():
            raise RFIDDeviceError("设备未连接")

        max_retries = 3  # 最大重试次数
        retry_delay = 0.1  # 重试延迟

        for retry in range(max_retries):
            try:
                # 清空接收缓冲区
                try:
                    self.ser.reset_input_buffer()
                except Exception as e:
                    # 如果重置缓冲区失败，可能设备已断开
                    self.log(f"重置输入缓冲区失败: {str(e)}")
                    self.ser = None
                    raise RFIDDeviceError("设备连接已断开")

                # 检查串口是否仍然打开
                if not self.ser.is_open:
                    self.ser = None
                    raise RFIDDeviceError("设备连接已关闭")

                # 发送命令
                bytes_written = self.ser.write(command)
                if bytes_written != len(command):
                    self.log(f"警告: 写入字节数不匹配 (期望: {len(command)}, 实际: {bytes_written})")

                # 等待响应 - 使用轮询机制避免无限等待
                response = bytearray()
                wait_time = 0
                max_wait = 1.0  # 最大等待1秒

                while wait_time < max_wait:
                    if self.ser.in_waiting > 0:
                        byte = self.ser.read()
                        response.extend(byte)
                        if byte == b'\x7E':  # 检测到结束符
                            break
                    else:
                        # 短暂等待后再次检查
                        time.sleep(0.01)
                        wait_time += 0.01

                # 检查响应是否为空
                if not response:
                    if retry < max_retries - 1:
                        self.log(f"未收到响应，正在重试... ({retry + 1}/{max_retries})")
                        time.sleep(retry_delay)
                        continue
                    else:
                        raise RFIDDeviceError("未收到设备响应")

                return response

            except serial.SerialException as e:
                # 串口异常，设备可能已断开
                self.log(f"串口异常: {str(e)}")
                self.ser = None
                raise RFIDDeviceError(f"设备通信异常: {str(e)}")

            except Exception as e:
                if retry < max_retries - 1:
                    self.log(f"命令发送错误，正在重试... ({retry + 1}/{max_retries}): {str(e)}")
                    time.sleep(retry_delay)
                else:
                    raise RFIDDeviceError(f"发送命令失败: {str(e)}")

        # 如果所有重试都失败
        raise RFIDDeviceError("多次尝试发送命令均失败")

    def read_card_once(self) -> Optional[Dict[str, str]]:
        """
        执行单次读卡操作
        
        返回:
            成功返回卡信息字典(包含rssi、pc、epc、crc字段)
            失败返回None
        """
        if not self.is_connected():
            self.log("设备未连接，无法读取卡号")
            return None

        command = bytearray([0xBB, 0x00, 0x22, 0x00, 0x00, 0x22, 0x7E])
        try:
            # 发送命令并获取响应
            response = self.send_command(command)

            # 详细记录响应信息用于调试
            if response:
                self.log(f"读卡响应长度: {len(response)}字节")
            else:
                self.log("读卡未收到响应")
                return None

            # 检查响应是否有效
            if len(response) < 8:
                self.log(f"响应数据长度不足 (收到 {len(response)} 字节)")
                return None

            # 读卡命令响应格式验证
            if response.startswith(bytearray([0xBB, 0x02, 0x22])):
                # 确保响应长度足够解析所有字段
                if len(response) < 22:
                    self.log(f"响应数据长度不足，无法解析卡片信息 (需要至少22字节，实际 {len(response)} 字节)")
                    return None

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

                self.log(f"单次读取成功 - PC: {pc}, EPC: {epc}, CRC: {crc}, RSSI: {rssi_dbm} dBm")
                return card_info
            elif response.startswith(bytearray([0xBB, 0x01, 0xFF])):
                # 错误响应，解析错误码
                if len(response) >= 7:
                    error_code = response[5]
                    self.log(f"单次读取返回错误: 错误码 0x{error_code:02X}")
                else:
                    self.log("单次读取返回错误响应，但格式不正确")
            else:
                # 其他未知响应
                self.log(f"单次读取返回未知响应: {response.hex().upper()}")

            self.log("单次读取失败")
            return None

        except RFIDDeviceError as e:
            self.log(f"读卡过程中设备错误: {str(e)}")
            # 如果通信出错，检查设备连接状态
            if self.ser is None or not self.ser.is_open:
                self.log("设备连接已断开，将尝试重新连接")
                if hasattr(self, 'last_port'):
                    try:
                        self.connect(self.last_port)
                    except:
                        pass
            return None
        except Exception as e:
            self.log(f"读卡错误: {str(e)}")
            return None

    def start_reading(self, callback: Callable[[Dict[str, str]], None]) -> bool:
        """
        启动群读模式
        
        参数:
            callback: 读取到卡时的回调函数,接收卡信息字典
            
        返回:
            操作是否成功
        """
        if not self.is_connected():
            self.log("设备未连接，无法进行群读")
            return False

        if self.group_read_active:
            self.log("群读已经在进行中")
            return True

        command = bytearray([0xBB, 0x00, 0x27, 0x00, 0x03, 0x22, 0xFF, 0xFF, 0x4A, 0x7E])
        try:
            self.send_command(command)
            self.log("群读启动命令已发送")
            self.log("开始群读")

            # 创建并启动读卡线程
            self.group_read_active = True
            self.read_thread = threading.Thread(
                target=self._read_thread_func,
                args=(callback,)
            )
            self.read_thread.daemon = True
            self.read_thread.start()

            return True
        except Exception as e:
            self.log(f"启动群读错误: {str(e)}")
            return False

    def _read_thread_func(self, callback: Callable[[Dict[str, str]], None]) -> None:
        """读卡线程函数"""
        buffer = bytearray()
        read_failed_logged = False

        while self.group_read_active and self.is_connected():
            try:
                # 读取可用数据
                data = self.ser.read(self.ser.in_waiting or 1)
                if data:
                    buffer += data
                    while True:
                        if len(buffer) < 1:
                            break
                        # 查找数据包起始标志 0xBB
                        if buffer[0] != 0xBB:
                            buffer.pop(0)
                            continue
                        if len(buffer) < 7:  # 最小包长度检查
                            break

                        # 解析数据包类型
                        frame_type = buffer[1]
                        command = buffer[2]

                        # 错误响应包 (BB 01 FF 00 01 15 16 7E)
                        if frame_type == 0x01 and command == 0xFF:
                            if len(buffer) >= 8:
                                buffer = buffer[8:]  # 跳过整个错误响应包
                                if not read_failed_logged:
                                    self.log("群读未识别到标签，读取卡号失败")
                                    read_failed_logged = True
                            else:
                                break
                        # 读取成功包（支持单次读取0x22和群读0x27的响应）
                        elif frame_type == 0x02 and (command == 0x22 or command == 0x27):
                            if len(buffer) < 24:  # 完整数据包长度检查
                                break

                            # 检查数据包完整性
                            if buffer[23] != 0x7E:  # 结束标志检查
                                buffer.pop(0)
                                continue

                            packet = buffer[:24]
                            buffer = buffer[24:]

                            # 检查数据长度字段
                            data_length = (packet[3] << 8) | packet[4]  # PL(MSB) PL(LSB)
                            if data_length != 0x11:  # 应该是17字节
                                continue

                            # 解析RSSI（有符号数转换）
                            rssi_raw = packet[5]
                            if rssi_raw > 127:  # 负数
                                rssi_dbm = -(256 - rssi_raw)
                            else:  # 正数
                                rssi_dbm = -rssi_raw

                            # PC值（2字节）
                            pc = f"{packet[6]:02X} {packet[7]:02X}"

                            # EPC值（12字节）
                            epc_bytes = packet[8:20]
                            epc = ' '.join([f"{b:02X}" for b in epc_bytes])

                            # CRC值（2字节）
                            crc = f"{packet[20]:02X} {packet[21]:02X}"

                            # 验证校验和
                            checksum = sum(packet[1:22]) & 0xFF  # 从Type到CRC的累加和
                            if checksum != packet[22]:
                                continue

                            # 创建包含所有信息的字典
                            card_info = {
                                'rssi': f"{rssi_dbm}",  # 转换为dBm的字符串
                                'pc': pc,
                                'epc': epc,
                                'crc': crc
                            }

                            # 执行回调
                            read_failed_logged = False
                            callback(card_info)
                        else:
                            # 未知包类型，丢弃当前字节
                            buffer.pop(0)
            except Exception as e:
                self.log(f"读卡线程错误: {str(e)}")
                break

    def stop_reading(self) -> bool:
        """
        停止群读模式
        
        返回:
            操作是否成功
        """
        if not self.is_connected():
            self.log("设备未连接，无法结束群读")
            return False

        if not self.group_read_active:
            return True  # 已经是停止状态

        command = bytearray([0xBB, 0x00, 0x28, 0x00, 0x00, 0x28, 0x7E])
        try:
            self.send_command(command)
            self.log("结束群读命令已发送")

            self.group_read_active = False
            # 等待线程结束
            if self.read_thread and self.read_thread.is_alive():
                self.read_thread.join(timeout=2.0)
            self.read_thread = None

            self.log("群读已结束")
            return True
        except Exception as e:
            self.log(f"停止群读错误: {str(e)}")
            return False

    def set_power(self, power_level: str) -> bool:
        """
        设置RFID读写器的发射功率
        
        参数:
            power_level: 功率级别,必须是POWER_COMMANDS中的一个键
            
        返回:
            设置是否成功
        """
        if not self.is_connected():
            self.log("设备未连接，无法设置功率")
            return False

        if power_level not in POWER_COMMANDS:
            self.log(f"无效的功率级别: {power_level}")
            return False

        command = POWER_COMMANDS[power_level]
        try:
            response = self.send_command(command)
            if response == SUCCESS_RESPONSE:
                self.log(f"发射功率设置成功: {power_level}")
                # 设置成功后重新获取实际功率值
                self.get_current_gain()
                return True
            else:
                self.log(f"发射功率设置失败: {response.hex().upper() if response else 'No response'}")
                return False
        except Exception as e:
            self.log(f"设置功率错误: {str(e)}")
            return False

    def get_current_gain(self) -> Optional[float]:
        """
        获取当前RFID读写器的增益值
        
        返回:
            成功返回增益值(dBm),失败返回None
        """
        if not self.is_connected():
            self.log("设备未连接，无法获取增益")
            return None

        # 增益查询命令
        command = bytearray([0xBB, 0x00, 0xB7, 0x00, 0x00, 0xB7, 0x7E])

        # 最大尝试次数
        max_attempts = 2

        for attempt in range(max_attempts):
            try:
                # 等待一小段时间确保设备稳定
                if attempt > 0:
                    time.sleep(0.5)
                    self.log(f"重新尝试获取增益 ({attempt + 1}/{max_attempts})")

                # 发送命令前检查连接状态
                if not self.is_connected():
                    self.log("设备连接已断开，无法获取增益")
                    return None

                # 发送命令并获取响应
                response = self.send_command(command)

                # 检查响应的有效性
                if response and len(response) >= 9:
                    expected_header = bytearray([0xBB, 0x01, 0xB7, 0x00, 0x02])
                    if response.startswith(expected_header):
                        # 解析增益值
                        pow_msb = response[5]
                        pow_lsb = response[6]
                        pow_value = (pow_msb << 8) | pow_lsb
                        self.gain = pow_value / 100
                        self.log(f"当前增益: {self.gain} dBm")
                        return self.gain
                    else:
                        self.log(f"响应格式不正确，无法解析增益: {response.hex().upper()}")
                else:
                    # 详细记录响应情况
                    if response:
                        self.log(f"接收到响应长度: {len(response)}，数据: {response.hex().upper()}")
                    else:
                        self.log("未收到响应数据")

                    if attempt < max_attempts - 1:
                        continue
                    else:
                        self.log("未收到设备增益响应，请检查设备是否为R200系列芯片")

            except RFIDDeviceError as e:
                # 如果是设备错误且不是最后一次尝试，则重试
                if attempt < max_attempts - 1:
                    self.log(f"获取增益出错，将重试: {str(e)}")
                    # 尝试重新建立连接
                    if self.ser is None and hasattr(self, 'last_port'):
                        self.log("尝试重新连接设备...")
                        try:
                            self.connect(self.last_port)
                        except:
                            pass
                else:
                    self.log(f"获取增益错误: {str(e)}")
                    return None

            except Exception as e:
                self.log(f"获取增益过程中发生意外错误: {str(e)}")
                return None

        return None

    def set_select_mode(self, mode: int) -> bool:
        """
        设置Select模式
        
        参数:
            mode: 0x00=所有操作都使用Select
                  0x01=不使用Select
                  0x02=除轮询外的操作使用Select
                  
        返回:
            设置是否成功
        """
        if not self.is_connected():
            self.log("设备未连接，无法设置Select模式")
            return False

        # 构建命令帧
        command = bytearray([
            0xBB,  # Header
            0x00,  # Type
            0x12,  # Command
            0x00,  # PL(MSB)
            0x01,  # PL(LSB)
            mode  # Mode
        ])
        # 计算校验和
        checksum = sum(command[1:6]) & 0xFF
        command.extend([checksum, 0x7E])

        try:
            response = self.send_command(command)

            # 验证响应帧
            if (response and
                    len(response) >= 8 and
                    response[0] == 0xBB and
                    response[1] == 0x01 and
                    response[2] == 0x12 and
                    response[3] == 0x00 and
                    response[4] == 0x01 and
                    response[5] == 0x00 and
                    response[7] == 0x7E):

                self.select_mode = mode
                mode_desc = {
                    0x00: "所有操作使用Select",
                    0x01: "不使用Select",
                    0x02: "除轮询外的操作使用Select"
                }
                self.log(f"Select模式已设置为: {mode_desc.get(mode, '未知模式')}")
                return True
            else:
                self.log("设置Select模式失败")
                return False
        except Exception as e:
            self.log(f"设置Select模式错误: {str(e)}")
            return False

    def set_select_params(self, target_epc: Optional[str] = None) -> bool:
        """
        设置Select参数
        
        参数:
            target_epc: 目标EPC，如果为None则清除Select
            
        返回:
            设置是否成功
        """
        if not self.is_connected():
            self.log("设备未连接，无法设置Select参数")
            return False

        if target_epc:
            try:
                # 移除空格并转换为字节数组
                epc_bytes = bytes.fromhex(target_epc.replace(" ", ""))

                # 检查EPC长度是否为12字节（96位）
                if len(epc_bytes) != 12:
                    self.log("错误：EPC必须为12字节（96位）")
                    return False

                # 构建命令帧
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

                # 计算校验和
                checksum = sum(command[1:24]) & 0xFF
                command.append(checksum)
                command.append(0x7E)

                # 发送命令并获取响应
                response = self.send_command(command)

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
                    self.log(f"成功设置Select参数，目标EPC: {target_epc}")

                    # 设置Select模式为除轮询外的操作使用Select (0x02)
                    self.set_select_mode(0x02)

                    return True
                else:
                    self.log("设置Select参数失败")
                    return False

            except ValueError as e:
                self.log(f"EPC格式错误: {str(e)}")
                return False
            except Exception as e:
                self.log(f"设置Select参数错误: {str(e)}")
                return False
        else:
            # 清除Select参数时设置模式为0x01（不使用Select）
            self.set_select_mode(0x01)
            self.select_param = None
            self.log("已清除Select参数")
            return True

    def write_card(self, data: str) -> bool:
        """
        向RFID标签写入数据
        
        参数:
            data: 要写入的16进制字符串数据
            
        返回:
            写入是否成功
        """
        if not self.is_connected():
            self.log("设备未连接，无法写入数据")
            return False

        if not data or len(data) > 32:  # 允许最多16字节（32个16进制字符）
            self.log("输入数据无效，请输入16字节以内的16进制字符串")
            return False

        try:
            data_bytes = bytes.fromhex(data.replace(" ", ""))

            # 限制数据长度
            if len(data_bytes) > 16:
                self.log(f"数据长度超过限制（最大16字节），当前长度: {len(data_bytes)}字节")
                return False

            # 构建写卡命令
            command = bytearray([
                0xBB,  # Header
                0x00,  # Type
                0x49,  # Command (写入标签)
                0x00,  # PL(MSB)
                0x11,  # PL(LSB)
                0x00, 0x00, 0x00, 0x00,  # 访问密码 (默认0)
                0x03,  # MemBank=3 (用户区)
                0x00, 0x00,  # WordAddr (起始地址，默认0)
                0x00,  # WordCnt (写入长度，按字计算)
                len(data_bytes)  # 实际写入的字节数
            ])

            # 添加数据
            command.extend(data_bytes)

            # 计算校验和
            command.append(sum(command[1:]) % 256)  # 添加校验和
            command.append(0x7E)  # 添加结束符

            # 发送命令并获取响应
            response = self.send_command(command)

            # 检查响应是否成功
            if response and response.startswith(bytearray([0xBB, 0x01, 0x49])):
                self.log("数据写入成功")
                return True
            else:
                self.log("数据写入失败")
                return False
        except ValueError as e:
            self.log(f"数据格式错误: {str(e)}")
            return False
        except Exception as e:
            self.log(f"写入过程出错: {str(e)}")
            return False

    def read_tag_memory(self,
                        access_password: str = "00000000",
                        membank: int = 0x01,
                        start_addr: int = 0x02,
                        length: int = 0x06) -> Optional[str]:
        """
        读取标签存储区数据
        
        参数:
            access_password: 访问密码，默认"00000000"
            membank: 存储区，0=保留区，1=EPC区，2=TID区，3=用户区
            start_addr: 起始地址，默认2（EPC区数据起始位置）
            length: 读取长度，单位为字（2字节），默认6（12字节EPC）
            
        返回:
            成功返回读取到的数据（16进制字符串），失败返回None
        """
        if not self.is_connected():
            self.log("设备未连接，无法读取标签数据")
            return None

        try:
            # 确保访问密码是8位16进制字符（4字节）
            if not access_password or len(access_password) == 0:
                access_password = "00000000"
            elif len(access_password) < 8:
                access_password = access_password.zfill(8)  # 不足8位前面补0

            # 转换访问密码为字节数组
            try:
                pwd_bytes = bytes.fromhex(access_password)
                if len(pwd_bytes) != 4:  # 4字节密码
                    self.log(f"错误：访问密码必须是4字节（8位16进制数），当前长度：{len(pwd_bytes)}字节")
                    return None
            except ValueError as e:
                self.log(f"错误：访问密码格式无效，必须是有效的16进制数：{str(e)}")
                return None

            # 构建命令
            command = bytearray([
                0xBB,  # 帧头
                0x00,  # Type
                0x39,  # Command (读标签)
                0x00,  # PL(MSB)
                0x09,  # PL(LSB)
            ])

            # 添加访问密码（4字节）
            command.extend(pwd_bytes)

            # 添加存储区参数
            command.extend([
                membank & 0xFF,  # MemBank
                start_addr & 0xFF,  # 起始地址低字节
                (start_addr >> 8) & 0xFF,  # 起始地址高字节
                length & 0xFF,  # 长度低字节
                (length >> 8) & 0xFF  # 长度高字节
            ])

            # 计算校验和
            checksum = sum(command[1:]) & 0xFF
            command.append(checksum)
            command.append(0x7E)  # 帧尾

            # 发送命令并获取响应
            response = self.send_command(command)

            # 解析响应
            if (response and
                    len(response) >= 8 and
                    response[0] == 0xBB and
                    response[1] == 0x01 and
                    response[2] == 0x39):

                # 获取数据长度
                data_len = response[5]

                if len(response) >= (7 + data_len):
                    # 提取数据部分
                    data_bytes = response[6:(6 + data_len)]

                    # 转换为16进制字符串
                    hex_data = ' '.join([f"{b:02X}" for b in data_bytes])

                    self.log(f"读取标签数据成功: {hex_data}")
                    return hex_data
                else:
                    self.log("响应数据长度不足")
            else:
                self.log("读取标签数据失败")

            return None
        except Exception as e:
            self.log(f"读取标签数据出错: {str(e)}")
            return None

    def write_epc(self, new_epc: str, access_password: str = "00000000") -> bool:
        """
        写入新的EPC到标签
        
        参数:
            new_epc: 新的EPC值（16进制字符串，必须是12字节/24个16进制字符）
            access_password: 访问密码，默认"00000000"
            
        返回:
            写入是否成功
        """
        if not self.is_connected():
            self.log("设备未连接，无法写入EPC")
            return False

        try:
            # 检查和处理EPC
            new_epc = new_epc.replace(" ", "")  # 移除空格

            try:
                epc_bytes = bytes.fromhex(new_epc)
                if len(epc_bytes) != 12:  # EPC必须是12字节
                    self.log(f"错误：EPC数据必须是12字节（24个16进制字符），当前长度：{len(epc_bytes)}字节")
                    return False
            except ValueError as e:
                self.log(f"错误：EPC格式无效，必须是有效的16进制数：{str(e)}")
                return False

            # 处理访问密码
            if not access_password or len(access_password) == 0:
                access_password = "00000000"
            elif len(access_password) < 8:
                access_password = access_password.zfill(8)  # 不足8位前面补0

            # 转换访问密码为字节数组
            try:
                pwd_bytes = bytes.fromhex(access_password)
                if len(pwd_bytes) != 4:  # 4字节密码
                    self.log(f"错误：访问密码必须是4字节（8位16进制数），当前长度：{len(pwd_bytes)}字节")
                    return False
            except ValueError as e:
                self.log(f"错误：访问密码格式无效，必须是有效的16进制数：{str(e)}")
                return False

            # 构建写入EPC命令
            command = bytearray([
                0xBB,  # Header
                0x00,  # Type
                0x49,  # Command (写入标签)
                0x00,  # PL(MSB)
                0x11,  # PL(LSB)
            ])

            # 添加访问密码
            command.extend(pwd_bytes)

            # 添加写入参数
            command.extend([
                0x01,  # MemBank=1 (EPC区)
                0x02, 0x00,  # WordAddr=2 (EPC数据起始位置)
                0x06,  # WordCnt=6 (写入6个字，即12字节)
            ])

            # 添加要写入的EPC数据
            command.extend(epc_bytes)

            # 计算校验和
            command.append(sum(command[1:]) % 256)  # 添加校验和
            command.append(0x7E)  # 添加结束符

            # 发送命令并获取响应
            response = self.send_command(command)

            # 检查响应是否成功
            if response and response.startswith(bytearray([0xBB, 0x01, 0x49])):
                self.log(f"EPC写入成功: {new_epc}")
                return True
            else:
                self.log("EPC写入失败")
                return False
        except Exception as e:
            self.log(f"EPC写入过程出错: {str(e)}")
            return False


# 使用示例代码
if __name__ == "__main__":
    # 示例1: 简单连接和读卡
    def print_card(card_info):
        print(f"读取到卡片: EPC={card_info['epc']}, RSSI={card_info['rssi']} dBm")


    reader = RFIDReader()
    print("可用设备:")
    for port, desc in reader.list_devices():
        print(f"  {port}: {desc}")

    # 请替换为实际的COM端口
    if reader.list_devices():
        port = reader.list_devices()[0][0]
        print(f"\n尝试连接到 {port}...")
        if reader.connect(port):
            print("连接成功!")

            # 单次读卡
            print("\n执行单次读卡:")
            card = reader.read_card_once()
            if card:
                print(f"读取到卡片: {card}")

            # 群读示例
            print("\n开始群读 (5秒):")
            reader.start_reading(print_card)
            time.sleep(5)
            reader.stop_reading()

            # 断开连接
            reader.disconnect()
            print("设备已断开")
    else:
        print("未检测到可用设备")
