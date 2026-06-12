"""抽卡机器人核心模块"""

import json
import logging
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import pyautogui
from mss import mss

# PyInstaller 打包后的数据路径
if getattr(sys, 'frozen', False):
    _BASE_DIR = Path(sys.executable).parent
    _BUNDLE_DIR = Path(sys._MEIPASS)
else:
    _BASE_DIR = Path(__file__).parent
    _BUNDLE_DIR = _BASE_DIR

from config import (
    CACHE_FALLBACK_COOLDOWN,
    CACHE_FALLBACK_ENABLED,
    CACHE_FILE,
    CACHE_MIN_CONFIDENCE,
    CAPTURE_REGION,
    CLICK_DELAY,
    CLICK_PAUSE,
    INITIAL_STATE,
    MATCH_METHOD,
    MATCH_THRESHOLD,
    MAX_CYCLES,
    MOVE_DURATION,
    POST_ACTION_DELAY,
    SCAN_INTERVAL,
    STATES,
    USE_POSITION_CACHE,
)

logger = logging.getLogger("gacha-bot")
pyautogui.FAILSAFE = True
pyautogui.PAUSE = CLICK_PAUSE

TEMPLATE_DIR = _BUNDLE_DIR / "templates"
CACHE_PATH = _BASE_DIR / CACHE_FILE

MATCH_METHODS = {
    "TM_CCOEFF_NORMED": cv2.TM_CCOEFF_NORMED,
    "TM_CCOEFF": cv2.TM_CCOEFF,
    "TM_CCORR_NORMED": cv2.TM_CCORR_NORMED,
    "TM_CCORR": cv2.TM_CCORR,
    "TM_SQDIFF_NORMED": cv2.TM_SQDIFF_NORMED,
    "TM_SQDIFF": cv2.TM_SQDIFF,
}


class TemplateCache:
    """预加载模板图片，避免重复读盘"""

    def __init__(self) -> None:
        self._cache: dict[str, np.ndarray] = {}

    def get(self, name: str) -> np.ndarray:
        if name not in self._cache:
            path = TEMPLATE_DIR / name
            if not path.exists():
                raise FileNotFoundError(f"模板文件不存在: {path}")
            img = cv2.imread(str(path), cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError(f"无法读取模板图片: {path}")
            self._cache[name] = img
        return self._cache[name]

    def reload(self) -> None:
        self._cache.clear()


class PositionCache:
    """位置缓存：首轮成功匹配后记住屏幕坐标，后续兜底使用"""

    def __init__(self) -> None:
        self._data: dict[str, dict] = {}
        self._last_used: dict[str, float] = {}
        self._load()

    def _load(self) -> None:
        if CACHE_PATH.exists():
            try:
                self._data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
                logger.info("已加载位置缓存: %d 条", len(self._data))
            except (json.JSONDecodeError, OSError):
                self._data = {}

    def save(self) -> None:
        if not USE_POSITION_CACHE:
            return
        try:
            CACHE_PATH.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
        except OSError as e:
            logger.warning("保存位置缓存失败: %s", e)

    def _key(self, state: str, template: str) -> str:
        return f"{state}::{template}"

    def set(self, state: str, template: str, x: int, y: int, confidence: float) -> None:
        """存入缓存（仅在高置信度时调用）"""
        if not USE_POSITION_CACHE or confidence < CACHE_MIN_CONFIDENCE:
            return
        key = self._key(state, template)
        self._data[key] = {"x": x, "y": y, "confidence": confidence}
        logger.info("位置缓存: %s → (%d, %d) [%.2f]", key, x, y, confidence)
        self.save()

    def get(self, state: str, template: str) -> tuple[int, int] | None:
        """获取缓存位置，冷却期内返回 None"""
        if not CACHE_FALLBACK_ENABLED:
            return None
        key = self._key(state, template)
        entry = self._data.get(key)
        if entry is None:
            return None
        now = time.time()
        if key in self._last_used:
            if now - self._last_used[key] < CACHE_FALLBACK_COOLDOWN:
                return None
        self._last_used[key] = now
        logger.info("使用缓存位置: %s → (%d, %d)", key, entry["x"], entry["y"])
        return entry["x"], entry["y"]


class GachaBot:
    def __init__(self) -> None:
        self._running = False
        self._state = INITIAL_STATE
        self._state_entered_at = 0.0
        self._last_heartbeat = 0.0
        self._cycles = 0
        self._sct = mss()
        self._templates = TemplateCache()
        self._positions = PositionCache()
        self._match_method = MATCH_METHODS.get(MATCH_METHOD, cv2.TM_CCOEFF_NORMED)
        self._capture_region = CAPTURE_REGION

    def set_capture_region(self, region: tuple[int, int, int, int] | None) -> None:
        """动态设置截图区域"""
        self._capture_region = region

    # ---- 屏幕截图 -------------------------------------------------

    def capture(self) -> np.ndarray:
        """截取屏幕并转为 BGR numpy 数组"""
        if self._capture_region is None:
            monitor = self._sct.monitors[1]  # 主显示器
        else:
            left, top, width, height = self._capture_region
            monitor = {"left": left, "top": top, "width": width, "height": height}

        sct_img = self._sct.grab(monitor)
        frame = np.array(sct_img, dtype=np.uint8)
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

    # ---- 模板匹配 -------------------------------------------------

    def match_template(self, screenshot: np.ndarray, template_name: str) -> tuple[bool, int, int, float]:
        """在截图中匹配模板，返回 (是否找到, 中心x, 中心y, 置信度)"""
        template = self._templates.get(template_name)
        th, tw = template.shape[:2]
        sh, sw = screenshot.shape[:2]

        if th > sh or tw > sw:
            logger.debug("模板 %s 尺寸大于截图，跳过匹配", template_name)
            return False, 0, 0, 0.0

        result = cv2.matchTemplate(screenshot, template, self._match_method)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if self._match_method in (cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED):
            matched = max_val <= (1.0 - MATCH_THRESHOLD)
        else:
            matched = max_val >= MATCH_THRESHOLD

        cx = max_loc[0] + tw // 2
        cy = max_loc[1] + th // 2
        logger.debug("模板 %s: max_val=%.3f, matched=%s", template_name, max_val, matched)
        return matched, cx, cy, max_val

    # ---- 鼠标动作 -------------------------------------------------

    def click_at(self, screen_x: int, screen_y: int) -> None:
        """点击屏幕坐标"""
        logger.info("点击 (%d, %d)", screen_x, screen_y)
        pyautogui.moveTo(screen_x, screen_y, duration=MOVE_DURATION)
        pyautogui.click(screen_x, screen_y)
        time.sleep(CLICK_DELAY)

    def to_screen_coords(self, local_x: int, local_y: int) -> tuple[int, int]:
        """将截图局部坐标转换为屏幕绝对坐标"""
        if self._capture_region:
            return local_x + self._capture_region[0], local_y + self._capture_region[1]
        return local_x, local_y

    # ---- 状态机 ---------------------------------------------------

    def _find_click_target(self, screenshot: np.ndarray, rule: dict, fallback_cx: int, fallback_cy: int) -> tuple[int, int] | None:
        """解析点击目标坐标，返回 None 表示无法确定有效坐标（跳过点击）。"""
        click_target = rule.get("click_target")
        if click_target:
            found, t_cx, t_cy, _ = self.match_template(screenshot, click_target)
            if found:
                return self.to_screen_coords(t_cx, t_cy)
            else:
                logger.warning("click_target '%s' 未匹配到，跳过点击", click_target)
                return None

        offset = tuple(rule.get("click_offset", (0, 0)))
        sx, sy = self.to_screen_coords(fallback_cx, fallback_cy)
        return sx + offset[0], sy + offset[1]

    def _execute_action(self, screenshot: np.ndarray, rule: dict, cx: int, cy: int, confidence: float) -> bool:
        """执行规则动作，返回是否成功执行"""
        template = rule["template"]
        action = rule.get("action", "click")

        if action == "click":
            result = self._find_click_target(screenshot, rule, cx, cy)
            if result is None:
                return False
            self.click_at(*result)
            # 高置信度匹配 → 存入位置缓存
            if template != "__always__":
                self._positions.set(self._state, template, result[0], result[1], confidence)
        elif action == "wait":
            wait_time = rule.get("wait_seconds", 1.0)
            logger.info("等待 %.1f 秒", wait_time)
            time.sleep(wait_time)
        elif action == "none":
            pass

        return True

    def _transition(self, rule: dict) -> None:
        """状态转移"""
        next_state = rule.get("next", self._state)
        if next_state != self._state:
            logger.info("状态切换: %s -> %s", self._state, next_state)
            self._state = next_state
            self._state_entered_at = time.time()
            self._last_heartbeat = time.time()
            if self._state == INITIAL_STATE:
                self._cycles += 1
                logger.info("===== 第 %d 抽完成 =====", self._cycles)

    def _try_position_cache(self, rules: list[dict]) -> bool:
        """尝试用缓存位置兜底，返回 True 表示执行了缓存点击"""
        for rule in rules:
            template = rule["template"]
            if template == "__always__":
                continue
            cached = self._positions.get(self._state, template)
            if cached is not None:
                logger.info("缓存兜底! %s::%s → (%d, %d)", self._state, template, cached[0], cached[1])
                self.click_at(*cached)
                self._transition(rule)
                time.sleep(POST_ACTION_DELAY)
                return True
        return False

    def step(self) -> bool:
        """
        执行一步状态机逻辑。
        返回 True 表示执行了一个动作（发生了状态转换），
        返回 False 表示本轮没有匹配到任何模板。
        """
        rules = STATES.get(self._state, [])
        if not rules:
            logger.warning("状态 '%s' 没有定义规则，保持当前状态", self._state)
            return False

        screenshot = self.capture()

        for rule in rules:
            template = rule["template"]

            if template == "__always__":
                if self._execute_action(screenshot, rule, 0, 0, 1.0):
                    self._transition(rule)
                    time.sleep(POST_ACTION_DELAY)
                    return True
                continue

            found, cx, cy, confidence = self.match_template(screenshot, template)
            if found:
                if self._execute_action(screenshot, rule, cx, cy, confidence):
                    self._transition(rule)
                    time.sleep(POST_ACTION_DELAY)
                return True

        # 没有规则匹配 —— 先尝试缓存兜底，再检查超时
        if self._try_position_cache(rules):
            return True

        now = time.time()
        elapsed = now - self._state_entered_at
        if now - self._last_heartbeat >= 10:
            logger.info("等待中... 状态: %s (已等待 %.0f 秒)", self._state, elapsed)
            self._last_heartbeat = now

        for rule in rules:
            timeout = rule.get("timeout")
            if timeout and elapsed >= timeout:
                timeout_next = rule.get("timeout_next")
                if timeout_next:
                    logger.info("状态 '%s' 超时 (%.1fs / %ss), 切换: -> %s",
                                self._state, elapsed, timeout, timeout_next)
                    # 超时时直接点击目标（省去中间状态）
                    timeout_click = rule.get("timeout_click_target")
                    if timeout_click:
                        found, t_cx, t_cy, _ = self.match_template(screenshot, timeout_click)
                        if found:
                            sx, sy = self.to_screen_coords(t_cx, t_cy)
                            self.click_at(sx, sy)
                        else:
                            logger.warning("timeout_click_target '%s' 未匹配，跳过点击", timeout_click)
                    self._state = timeout_next
                    self._state_entered_at = time.time()
                    self._last_heartbeat = time.time()
                    return True
                break

        return False

    # ---- 主循环 ---------------------------------------------------

    def run_once(self) -> None:
        """运行一轮扫描"""
        if not self._running:
            return

        acted = self.step()
        if not acted:
            time.sleep(SCAN_INTERVAL)

    def start(self) -> None:
        logger.info("抽卡机器人启动，初始状态: %s", self._state)
        logger.info("按 %s 紧急停止", "STOP_KEY (见 config.py)")

        self._running = True
        try:
            while self._running:
                self.run_once()
                if MAX_CYCLES > 0 and self._cycles >= MAX_CYCLES:
                    logger.info("已达到最大循环次数 %d，停止", MAX_CYCLES)
                    break
        except KeyboardInterrupt:
            logger.info("收到中断信号")
        finally:
            self.stop()

    def stop(self) -> None:
        self._running = False
        self._sct.close()
        logger.info("机器人已停止，共完成 %d 轮", self._cycles)

    @property
    def state(self) -> str:
        return self._state

    @property
    def running(self) -> bool:
        return self._running
