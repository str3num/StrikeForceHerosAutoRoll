# 战火英雄自动抽卡 (StrikeForceHeros Auto Roll)

基于 OpenCV 模板匹配的自动化抽卡脚本，支持视觉识别屏幕按钮并自动点击。

> Author: **chuqing**

## 功能

- 视觉识别游戏界面按钮（roll / save / sell 等）
- 可配置的状态机流程，适配不同游戏的抽卡逻辑
- 稀有度自动判断（全金保留 / 低稀有度卖掉）
- 位置缓存兜底，首轮成功后即使匹配置信度下降也能稳定运行
- 预览调试模式（不点击，显示匹配结果）
- F9/F10 快捷定位游戏窗口区域
- PyInstaller 一键打包为 EXE

## 环境要求

- Windows 10/11
- Python 3.10+（源码运行）
- 游戏建议 **1280×720 左右窗口化** 运行

## 快速开始

### 源码运行

```bash
pip install -r requirements.txt
python main.py run
```

### 打包运行

双击 `build.bat` 一键打包，输出在 `dist\ZhanHuo\`，运行 `ZhanHuo.exe`。

## 使用说明

### 热键

| 按键 | 功能 |
|------|------|
| F6 | 启动机器人 |
| F7 | 暂停 |
| F8 | 退出 |
| F9 | 记录游戏窗口左上角 |
| F10 | 记录游戏窗口右下角 |

### 操作步骤

1. 启动程序，选择 `1. 运行机器人`
2. 鼠标移到游戏窗口**左上角** → 按 **F9**
3. 鼠标移到游戏窗口**右下角** → 按 **F10**
4. 按 **F6** 开始自动抽卡

### 预览模式

选择 `2. 预览模式`，先设好 F9/F10 区域后会自动打开预览窗口：
- 绿色框 = 匹配成功
- 红色框 = 未匹配
- 青色框 = 点击目标
- **ESC** = 切换状态
- **Q** = 退出

## 配置

编辑 `config.py` 调整参数：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `MATCH_THRESHOLD` | 匹配置信度阈值 | 0.77 |
| `SCAN_INTERVAL` | 扫描间隔(秒) | 0.5 |
| `USE_POSITION_CACHE` | 启用位置缓存 | True |
| `CACHE_FALLBACK_COOLDOWN` | 缓存冷却(秒) | 10 |
| `STATES` | 状态机流程配置 | 见文件 |

## 目录结构

```
├── main.py            # 入口
├── bot.py             # 核心引擎
├── config.py          # 配置文件
├── requirements.txt   # Python 依赖
├── build.bat          # 打包脚本
├── run.bat            # Windows 启动
├── preview.bat        # 预览模式启动
├── capture.bat        # 模板截取
└── templates/         # 模板图片
```

## License

MIT
