import time

import serial
import serial.tools.list_ports
from PySide6.QtCore import QThread, Signal

# 功率配置字典：定义不同功率值对应的命令字节
POWER_COMMANDS = {
    "12.5 dBm (0.6m)": bytearray([0xBB, 0x00, 0xB6, 0x00, 0x02, 0x04, 0xE2, 0x9E, 0x7E]),
    "14 dBm (0.8m)": bytearray([0xBB, 0x00, 0xB6, 0x00, 0x02, 0x05, 0x78, 0x35, 0x7E]),
    "15.5 dBm (0.9m)": bytearray([0xBB, 0x00, 0xB6, 0x00, 0x02, 0x06, 0x0E, 0xCC, 0x7E]),
    "17 dBm (1m)": bytearray([0xBB, 0x00, 0xB6, 0x00, 0x02, 0x06, 0xA4, 0x62, 0x7E]),
    "18.5 dBm (1.15m)": bytearray([0xBB, 0x00, 0xB6, 0x00, 0x02, 0x07, 0x3A, 0xF9, 0x7E]),
    "20 dBm (2m)": bytearray([0xBB, 0x00, 0xB6, 0x00, 0x02, 0x07, 0xD0, 0x8F, 0x7E]),
}

# 成功响应的标准字节序列
SUCCESS_RESPONSE = bytearray([0xBB, 0x01, 0xB6, 0x00, 0x01, 0x00, 0xB8, 0x7E])


def checksum(data):
    """
    计算数据的校验和
    参数:
        data: 需要计算校验和的数据
    返回:
        校验和结果（8位）
    """
    return sum(data) & 0xFF


def send_command(ser, command):
    """
    向设备发送命令并读取响应
    参数:
        ser: 串口对象
        command: 要发送的命令字节序列
    返回:
        设备的响应数据
    异常:
        SerialException: 串口通信错误
        Exception: 其他错误
    """
    try:
        if ser is None or not ser.is_open:
            raise serial.SerialException("串口未连接或已断开")

        ser.write(command)
        time.sleep(0.1)  # 等待设备响应
        response = ser.read_all()
        return response
    except serial.SerialException as e:
        raise e
    except Exception as e:
        raise Exception(f"命令发送失败: {e}")


def list_com_ports():
    """
    列出系统中所有可用的COM端口
    返回:
        包含(端口名, 描述)元组的列表
    """
    ports = serial.tools.list_ports.comports()
    return [(port.device, port.description) for port in ports]


def connect_to_device(port, baudrate=115200, timeout=1):
    """
    连接到指定的串口设备
    参数:
        port: 串口端口名
        baudrate: 波特率，默认115200
        timeout: 超时时间，默认1秒
    返回:
        成功返回Serial对象，失败返回None
    """
    try:
        ser = serial.Serial(port, baudrate, timeout=timeout)
        return ser
    except serial.SerialException:
        return None


class SerialReadThread(QThread):
    """
    串口读取线程类
    用于异步读取串口数据，避免阻塞主线程
    """
    # 定义信号
    card_readed = Signal(dict)  # 读取到卡号时发送信号
    read_failed = Signal()  # 读取失败时发送信号
    error_occurred = Signal(str)  # 发生错误时发送信号

    def __init__(self, ser):
        """
        初始化串口读取线程
        参数:
            ser: 串口对象
        """
        super().__init__()
        self.ser = ser
        self._running = True

    def run(self):
        """
        线程主循环
        实现了RFID读卡器协议的解析逻辑
        """
        buffer = bytearray()
        while self._running and self.ser and self.ser.is_open:
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
                                self.read_failed.emit()
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
                            
                            self.card_readed.emit(card_info)
                        else:
                            # 未知包类型，丢弃当前字节
                            buffer.pop(0)
            except Exception as e:
                self.error_occurred.emit(str(e))
                break

    def stop(self):
        """
        停止线程运行
        """
        self._running = False
        self.wait()  # 等待线程结束
