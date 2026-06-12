"""抽卡机器人配置"""

# ============================================================
# 屏幕截图区域 (left, top, width, height)，None 表示全屏
# 建议只截取游戏窗口区域以提升识别速度和准确率
# ============================================================
CAPTURE_REGION: tuple | None = None
# 示例: CAPTURE_REGION = (0, 0, 1920, 1080)

# ============================================================
# 模板匹配设置
# ============================================================
MATCH_THRESHOLD = 0.77       # 匹配置信度阈值 (0~1)，越高越严格
MATCH_METHOD = "TM_CCOEFF_NORMED"  # 匹配算法

# ============================================================
# 点击设置
# ============================================================
CLICK_DELAY = 0.1            # 点击后等待秒数
MOVE_DURATION = 0.15         # 鼠标移动耗时
CLICK_PAUSE = 0.05           # 按下到释放的间隔

# ============================================================
# 循环间隔
# ============================================================
SCAN_INTERVAL = 0.5          # 每轮扫描间隔秒数
POST_ACTION_DELAY = 0.8      # 动作后的等待时间

# ============================================================
# 热键
# ============================================================
START_KEY = "f6"             # 启动热键
STOP_KEY = "f7"              # 紧急停止热键
EXIT_KEY = "f8"              # 退出程序热键

# ============================================================
# 抽卡状态机流程
# 每个状态定义需要检测的模板和对应的动作
#
# 字段说明:
#   template: 模板图片文件名 (放在 templates/ 目录下)
#   action:   "click" 点击模板中心, "wait" 等待, "none" 不做任何事
#   next:     匹配成功后切换到的下一个状态
#   timeout:  此状态超时秒数, 超时后进入 timeout_next
#   timeout_next: 超时后进入的状态 (可选)
#   click_offset: 点击相对模板中心的偏移 (x, y), 默认 (0, 0)
# ============================================================
STATES: dict[str, list[dict]] = {
    # 状态1: 检测抽卡界面，点击 roll 按钮开始抽卡
    #   多个 roll 变体按顺序匹配，提高不同光照/场景下的识别率
    "detect_roll": [
        {"template": "roll.png",  "action": "click", "next": "wait_result"},
        {"template": "roll2.png", "action": "click", "next": "wait_result"},
        {"template": "roll3.png", "action": "click", "next": "wait_result"},
        {"template": "roll4.png", "action": "click", "next": "wait_result"},
        {"template": "roll5.png", "action": "click", "next": "wait_result"},
        {"template": "roll6.png", "action": "click", "next": "wait_result"},
    ],

    # 状态2: 等待抽卡动画，约2秒后出现结果界面
    "wait_result": [
        {
            "template": "__always__",
            "action": "wait",
            "wait_seconds": 6,
            "next": "check_level",
        },
    ],

    # 状态3: 判断稀有度
    #   规则按顺序匹配，先看是不是全金(level.png)，
    #   再逐个匹配反例(QQ*.png)，都没命中就超时卖掉
    "check_level": [
        # 全金/高稀有度 → 保留
        {
            "template": "level.png",
            "action": "click",
            "click_target": "save.png",
            "next": "wait_back_to_roll",
            "timeout": 0.5,
            "timeout_next": "detect_roll",
            "timeout_click_target": "sell.png",
        },
        {"template": "level2.png", "action": "click", "click_target": "save.png", "next": "wait_back_to_roll"},
        {"template": "level3.png", "action": "click", "click_target": "save.png", "next": "wait_back_to_roll"},

    ],

    # 状态5: 等待界面切换回抽卡页（save/sell 后过渡动画）
    "wait_back_to_roll": [
        {
            "template": "__always__",
            "action": "wait",
            "wait_seconds": 0.5,
            "next": "detect_roll",
        },
    ],
}

# 起始状态
INITIAL_STATE = "detect_roll"

# ============================================================
# 位置缓存 —— 首轮成功后记住坐标，后续匹配置信度低时用缓存兜底
# ============================================================
USE_POSITION_CACHE = True           # 是否启用位置缓存
CACHE_FILE = "positions.json"       # 缓存文件路径
CACHE_MIN_CONFIDENCE = 0.85         # 只有置信度高于此值才存入缓存
CACHE_FALLBACK_ENABLED = True       # 匹配失败时是否使用缓存位置兜底
CACHE_FALLBACK_COOLDOWN = 10        # 缓存兜底冷却秒数，避免同一位置反复点

# ============================================================
# 日志级别: "DEBUG" | "INFO" | "WARNING"
# ============================================================
LOG_LEVEL = "INFO"

# ============================================================
# 运行次数限制 (0 表示无限循环)
# ============================================================
MAX_CYCLES = 0
