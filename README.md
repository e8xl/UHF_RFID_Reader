# RFID资产管理系统

## 项目介绍

RFID资产管理系统是一款基于PySide6开发的GUI程序，旨在实现RFID标签的读取、写入及资产管理功能。系统支持与R200系列UHF读卡器进行通信，提供友好的用户界面和丰富的功能，帮助用户高效地进行资产管理和RFID数据处理。

## 功能特性

### 基础功能
- 串口设备的自动扫描与智能连接管理
- 实时显示读取结果和详细操作日志
- 读写器功率和增益的动态调节与显示
- 支持断线自动重连和异常处理机制

### RFID操作
- RFID标签的单次读取和连续群读功能
- 支持EPC数据的写入和验证
- Select模式支持(可选择性读取特定EPC标签)
- 支持多种Select操作模式(全局/部分/禁用)
- Select参数的设置、验证和清除功能

### 资产管理
- 群体搜索功能(支持批量搜索和匹配标签)
- 实时卡号匹配与验证系统
- 资产搜索功能(支持与数据库内资产信息实时匹配)
- 搜索历史记录管理(记录搜索时间、设备和匹配结果)
- 资产管理报表(支持搜索历史的统计和导出)

### 用户界面
- 基于PySide6的现代化GUI界面
- 多页面分层管理(主页/写入/搜索/资产/匹配/设置/调试)
- 实时状态显示和反馈系统
- 智能的错误提示和处理机制
- 支持界面自适应不同屏幕分辨率

## 技术栈

- Python 3.8+
- PySide6
- pyserial
- QFluentWidgets
- SQLite3

## 安装与依赖

1. 确保已安装Python 3.8或更高版本
2. 安装所需依赖包：

```bash
pip install PySide6 pyserial qfluentwidgets
```

## 使用方法

直接运行主程序文件启动应用：

```bash
python RFID_AssetManager.py
```

## 界面说明

系统包含以下主要界面：

1. **主界面(主页)**：用于连接设备和进行读卡器基础操作
2. **写入界面**：用于给标签更改EPC卡号
3. **搜索界面**：搜索附近卡号并与数据库内资产值匹配
4. **资产界面**：记录群体搜索的匹配日期、搜索设备名称等信息
5. **匹配界面**：设定固定EPC卡号，找寻周围卡号并匹配数据库
6. **设置界面**：调整读写器功率设置
7. **调试界面**：用于调试和测试功能

## 操作流程

1. 在主界面扫描并连接可用的COM端口设备
2. 连接成功后可进行单次读卡或启动群读模式
3. 使用写入界面可以修改标签的EPC值
4. 在搜索界面可以执行资产搜索和匹配操作
5. 资产界面查看历史搜索记录
6. 通过设置界面调整读写器功率和其他参数

## RFID_Moudel模块

项目包含RFID_Moudel目录，其中提供了一系列用于RFID操作的核心函数和接口。该模块有自己的详细README文档，具体使用方法请参考该目录下的README.md文件。该模块主要包含：

- 核心RFID操作功能
- 读写卡片示例
- 集成应用示例

## 版本信息

- 当前版本：V1.1.0
- 创建日期：2025/02

## 许可证

MIT License
