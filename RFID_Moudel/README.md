文档使用 claude 3.7-sonnet 生成

# RFID核心功能模块技术文档

## 目录

1. [简介](#1-简介)
2. [系统架构](#2-系统架构)
3. [核心组件](#3-核心组件)
4. [API参考](#4-api参考)
5. [使用场景与示例](#5-使用场景与示例)
6. [技术规格](#6-技术规格)
7. [集成指南](#7-集成指南)
8. [故障排查](#8-故障排查)
9. [附录](#9-附录)

## 1. 简介

RFID核心功能模块（rfid_core.py）是一个独立的Python库，提供对UHF RFID读卡器（特别是R200系列）的底层控制功能。该模块从RFID_AssetManager项目中提取核心功能，允许在不依赖GUI的情况下使用RFID读卡器的基本功能。

### 1.1 功能概述

- 设备连接与断开管理
- 设备搜索与自动识别
- 单次读卡操作
- 连续群读（多标签识别）
- 读卡器功率设置与调整
- Select模式操作（标签过滤）
- 强大的多线程实现
- **自动重连与错误恢复机制**
- **健壮的通信协议实现**
- **标签数据写入功能**

### 1.2 应用场景

- 资产管理系统
- 仓库库存管理
- 物流跟踪系统
- 生产线自动化
- 零售库存盘点
- 安全门禁控制
- 标签数据读写系统

## 2. 系统架构

RFID核心功能模块采用分层架构设计，将底层硬件通信与上层应用逻辑分离，提供了清晰的API接口。

### 2.1 架构层次

1. **硬件通信层**: 负责与RFID读卡器的串口通信
2. **通信稳定层**: 负责处理连接中断、重试和自动恢复
3. **协议解析层**: 实现RFID读卡器通信协议的编码和解码
4. **功能服务层**: 提供读卡、群读、功率设置等核心功能
5. **应用接口层**: 为上层应用提供简洁统一的API

### 2.2 模块关系

```
应用程序 -----> RFID核心模块 -----> 硬件设备
   |              |                  |
   |              |                  |
集成示例        功能接口           R200系列读卡器
(应用层)        (接口层)          (硬件层)
```

## 3. 核心组件

### 3.1 RFIDReader类

`RFIDReader`类是模块的核心，封装了与RFID设备的所有交互功能：

- 设备连接与管理
- 卡片读取操作
- 群读线程控制
- 命令发送与响应处理
- 错误恢复与重试机制
- 标签数据写入功能

### 3.2 通信协议处理

模块实现了与R200系列RFID读卡器的通信协议，包括：

- 命令帧格式化
- 响应解析
- 校验和计算
- 错误处理与恢复
- 超时与重试机制
- 连接状态管理

### 3.3 多线程实现

采用线程安全的设计，确保群读操作可靠稳定：

- 非阻塞式群读实现
- 线程管理与控制
- 数据缓冲与处理
- 异常处理与恢复

## 4. API参考

### 4.1 RFIDReader类

#### 初始化

```python
def __init__(self, log_callback: Optional[Callable[[str], None]] = None)
```

参数:
- `log_callback`: 日志回调函数，用于输出日志信息（可选）

#### 设备管理

```python
def list_devices() -> List[Tuple[str, str]]
```
列出系统中所有可用的COM端口，返回包含(端口名, 描述)元组的列表。

```python
def connect(self, port: str, baudrate: int = 115200, timeout: int = 1) -> bool
```
连接到指定的串口设备，返回连接是否成功。连接成功后会记录端口名称，用于自动重连。

```python
def disconnect(self) -> bool
```
断开当前连接的设备，返回操作是否成功。

```python
def is_connected(self) -> bool
```
检查设备是否已连接，返回布尔值。

#### 读卡操作

```python
def read_card_once(self) -> Optional[Dict[str, str]]
```
执行单次读卡操作，成功返回卡信息字典，失败返回None。包含错误恢复机制，在通信出错时自动尝试重连。

```python
def start_reading(self, callback: Callable[[Dict[str, str]], None]) -> bool
```
启动群读模式，需提供读取到卡时的回调函数，返回操作是否成功。

```python
def stop_reading(self) -> bool
```
停止群读模式，返回操作是否成功。

#### 数据写入操作

```python
def write_card(self, data: str) -> bool
```
将数据写入RFID标签的用户区，参数为16进制字符串，返回写入是否成功。

```python
def write_epc(self, new_epc: str, access_password: str = "00000000") -> bool
```
写入新的EPC到标签，参数为EPC的16进制字符串和访问密码，返回写入是否成功。

```python
def read_tag_memory(self, access_password: str = "00000000", 
                   membank: int = 0x01, start_addr: int = 0x02, 
                   length: int = 0x06) -> Optional[str]
```
读取标签特定存储区的数据，返回16进制格式的数据字符串或失败时返回None。

#### 设备控制

```python
def send_command(self, command: bytearray) -> bytearray
```
发送命令到RFID设备并获取响应。包含自动重试机制，最多尝试3次，提高通信可靠性。

```python
def set_power(self, power_level: str) -> bool
```
设置RFID读写器的发射功率，返回设置是否成功。

```python
def get_current_gain(self) -> Optional[float]
```
获取当前RFID读写器的增益值，成功返回增益值(dBm)，失败返回None。增强了错误处理，在获取失败时可自动重试。

```python
def set_select_mode(self, mode: int) -> bool
```
设置Select模式，返回设置是否成功。

```python
def set_select_params(self, target_epc: Optional[str] = None) -> bool
```
设置Select参数，返回设置是否成功。

### 4.2 异常处理

```python
class RFIDDeviceError(Exception)
```
RFID设备操作异常类，用于表示设备通信和操作过程中的错误。

### 4.3 常量

```python
POWER_COMMANDS: Dict[str, bytearray]
```
功率配置字典，定义不同功率值对应的命令字节。

```python
SUCCESS_RESPONSE: bytearray
```
成功响应的标准字节序列。

## 5. 使用场景与示例

### 5.1 基本操作示例

以下是使用RFID核心模块进行基本操作的示例代码：

```python
from rfid_core import RFIDReader

# 创建读卡器实例
reader = RFIDReader()

# 列出可用设备
devices = reader.list_devices()
if devices:
    # 连接到第一个可用设备
    port = devices[0][0]
    if reader.connect(port):
        # 设置功率
        reader.set_power("17 dBm (1m)")
        
        # 单次读卡
        card = reader.read_card_once()
        if card:
            print(f"读取到卡片: EPC={card['epc']}")
        
        # 群读示例
        def handle_card(card_info):
            print(f"群读到卡片: EPC={card_info['epc']}")
        
        # 开始群读
        reader.start_reading(handle_card)
        
        # ... 进行其他操作 ...
        
        # 停止群读
        reader.stop_reading()
        
        # 断开连接
        reader.disconnect()
```

### 5.2 数据写入示例

使用模块写入EPC和读取标签数据：

```python
from rfid_core import RFIDReader

reader = RFIDReader()
if reader.connect("COM3"):
    # 读取当前EPC
    card = reader.read_card_once()
    if card:
        original_epc = card['epc']
        print(f"当前EPC: {original_epc}")
        
        # 写入新的EPC
        new_epc = "112233445566778899AABBCC"
        if reader.write_epc(new_epc):
            print(f"EPC写入成功: {new_epc}")
            
        # 读取用户区数据
        user_data = reader.read_tag_memory(
            membank=0x03,  # 用户区
            start_addr=0x00,
            length=2  # 读取4字节
        )
        if user_data:
            print(f"用户区数据: {user_data}")
            
        # 写入数据到用户区
        if reader.write_card("01020304"):
            print("数据写入用户区成功")
            
    reader.disconnect()
```

### 5.3 应用集成示例

模块可以轻松集成到更大的应用程序中，如`rfid_integration_example.py`所示：

```python
from rfid_core import RFIDReader
import threading
import time

class MyRFIDApplication:
    def __init__(self):
        # 创建RFID读卡器并配置日志回调
        self.reader = RFIDReader(log_callback=self.on_log)
        self.inventory = {}
        self.lock = threading.Lock()
    
    def on_log(self, message):
        print(f"[RFID] {message}")
    
    def on_card_read(self, card_info):
        with self.lock:
            epc = card_info['epc']
            if epc not in self.inventory:
                self.inventory[epc] = {
                    'first_seen': time.time(),
                    'count': 1
                }
                print(f"发现新卡片: {epc}")
            else:
                self.inventory[epc]['count'] += 1
    
    def start(self, port):
        if self.reader.connect(port):
            return self.reader.start_reading(self.on_card_read)
        return False
    
    def stop(self):
        self.reader.stop_reading()
        self.reader.disconnect()
```

## 6. 技术规格

### 6.1 硬件要求

- **支持设备**: R200系列UHF RFID读卡器
- **接口类型**: 串口（USB虚拟串口）
- **波特率**: 115200（默认）

### 6.2 协议规格

RFID读卡器命令帧格式：

| 字段    | 长度(字节) | 描述                         |
|---------|------------|------------------------------|
| Header  | 1          | 帧头标识，固定为0xBB         |
| Type    | 1          | 帧类型码                     |
| Command | 1          | 命令码                       |
| PL(MSB) | 1          | 参数长度高字节               |
| PL(LSB) | 1          | 参数长度低字节               |
| Data    | 可变       | 命令参数数据                 |
| Checksum| 1          | 校验和（从Type到Data的累加） |
| End     | 1          | 帧尾标识，固定为0x7E         |

### 6.3 功率级别

| 功率级别          | 有效读取距离 | 命令值          |
|-------------------|--------------|-----------------|
| 12.5 dBm (0.6m)   | 约0.6米      | 0x04, 0xE2      |
| 14 dBm (0.8m)     | 约0.8米      | 0x05, 0x78      |
| 15.5 dBm (0.9m)   | 约0.9米      | 0x06, 0x0E      |
| 17 dBm (1m)       | 约1米        | 0x06, 0xA4      |
| 18.5 dBm (1.15m)  | 约1.15米     | 0x07, 0x3A      |
| 20 dBm (2m)       | 约2米        | 0x07, 0xD0      |

### 6.4 Select模式

| 模式值 | 描述                       |
|--------|----------------------------|
| 0x00   | 所有操作都使用Select       |
| 0x01   | 不使用Select               |
| 0x02   | 除轮询外的操作使用Select   |

### 6.5 存储区编号

| 编号   | 存储区     | 描述                            |
|--------|------------|---------------------------------|
| 0x00   | 保留区     | 包含密码和锁定状态              |
| 0x01   | EPC区      | 存储EPC编码                     |
| 0x02   | TID区      | 标签ID，通常为只读              |
| 0x03   | 用户区     | 用户自定义数据存储区            |

## 7. 集成指南

### 7.1 基本集成步骤

1. **导入模块**: 将`rfid_core.py`文件复制到项目目录或安装为Python包
2. **创建实例**: 实例化`RFIDReader`类
3. **连接设备**: 使用`connect()`方法连接到指定设备
4. **实现回调**: 设计处理读卡结果的回调函数
5. **启动操作**: 根据需要调用读卡或群读功能
6. **处理异常**: 捕获并处理可能的`RFIDDeviceError`异常
7. **资源释放**: 操作完成后调用`disconnect()`释放资源

### 7.2 错误处理与恢复

模块已内置自动错误恢复机制，以下是部分实现：

- **命令重试机制**: 命令发送失败自动重试，最多3次
- **自动重连功能**: 连接丢失时尝试自动重连
- **超时保护**: 防止长时间等待无响应的设备
- **响应验证**: 验证响应数据的完整性和正确性

典型错误处理示例：

```python
try:
    reader.connect(port)
    reader.start_reading(callback)
except RFIDDeviceError as e:
    print(f"设备操作错误: {str(e)}")
    # 模块会自动尝试恢复，但如果需要，也可以在这里进行手动处理
finally:
    reader.disconnect()  # 确保资源释放
```

### 7.3 线程安全注意事项

- 回调函数会在单独线程中执行，需确保处理逻辑是线程安全的
- 使用锁机制保护共享资源访问
- 避免在回调函数中执行长时间阻塞操作
- 群读操作完成后务必调用`stop_reading()`释放线程资源

## 8. 故障排查

### 8.1 常见问题及解决方案

| 问题                     | 可能原因                           | 解决方案                                  |
|--------------------------|------------------------------------|-----------------------------------------|
| 无法连接设备             | 设备未连接或USB线松动              | 检查USB连接，更换USB端口                 |
|                          | 驱动未正确安装                     | 重新安装设备驱动                         |
|                          | 设备被其他程序占用                 | 关闭可能使用该串口的其他程序             |
| 获取增益失败             | 通信不稳定                         | 模块会自动重试，也可重启设备             |
|                          | 设备不支持该命令                   | 确认设备型号是否为R200系列               |
| 读卡操作无响应           | 标签不在读取范围内                 | 调整标签位置或增加功率                   |
|                          | 设备功率设置过低                   | 尝试增加功率等级                         |
|                          | 通信中断                           | 断开后重新连接设备                       |
| 写入操作失败             | 标签受保护或已锁定                 | 检查标签保护状态，提供正确的访问密码     |
|                          | 标签距离太远                       | 将标签移近读写器                         |
|                          | 数据格式错误                       | 确保数据为正确的16进制字符串格式         |

### 8.2 调试技巧

1. **启用详细日志**: 提供自定义日志回调函数以获取详细操作日志
2. **检查设备状态**: 使用`is_connected()`方法确认设备连接状态
3. **监控串口通信**: 使用串口监控工具观察通信过程 
4. **测试基本功能**: 先测试单次读卡等基本功能，再尝试复杂操作
5. **隔离环境**: 排除电磁干扰和其他设备的干扰

## 9. 附录

### 9.1 命令参考

| 命令类型 | 命令码 | 描述             |
|----------|--------|------------------|
| 0x22     | 0x22   | 单次读卡         |
| 0x27     | 0x27   | 开始群读         |
| 0x28     | 0x28   | 停止群读         |
| 0x39     | 0x39   | 读标签存储区     |
| 0x49     | 0x49   | 写标签           |
| 0xB6     | 0xB6   | 设置功率         |
| 0xB7     | 0xB7   | 获取当前功率/增益 |
| 0x12     | 0x12   | 设置Select模式   |
| 0x0C     | 0x0C   | 设置Select参数   |
| 0x0B     | 0x0B   | 获取Select参数   |

### 9.2 卡片信息格式

读取到的卡片信息包含以下字段：

| 字段名 | 类型   | 描述                                  |
|--------|--------|--------------------------------------|
| rssi   | 字符串 | 信号强度，单位dBm，值越大信号越强     |
| pc     | 字符串 | PC值，16进制格式，带空格分隔          |
| epc    | 字符串 | EPC编码，16进制格式，带空格分隔       |
| crc    | 字符串 | CRC校验码，16进制格式，带空格分隔     |

### 9.3 错误码说明

常见错误处理:

- 设备未连接错误: "设备未连接"或"设备连接已断开"
- 命令发送失败: "发送命令失败: {具体原因}"
- 超时错误: "未收到设备响应"
- 读卡失败: "单次读取失败"或"群读未识别到标签"
- 功率设置失败: "发射功率设置失败: {响应数据}"
- 连接错误: "连接失败: {具体原因}"
- 参数错误: "数据格式错误"或"EPC格式无效"

---
