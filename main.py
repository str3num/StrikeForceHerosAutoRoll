#!/usr/bin/env python3
"""自动化抽卡脚本入口

使用方式:
  1. 安装依赖:  pip install -r requirements.txt
  2. 截取模板:  python main.py capture <模板名>
  3. 编辑配置:  修改 config.py 中的状态机流程
  4. 启动机器人: python main.py run

热键:
  F6 - 启动
  F7 - 紧急停止
  F8 - 退出程序
"""

import argparse
import logging
import sys
import time
from pathlib import Path

import cv2
import pyautogui
from pynput.keyboard import Key, Listener

from bot import GachaBot, TEMPLATE_DIR
from config import EXIT_KEY, LOG_LEVEL, START_KEY, STOP_KEY

logger = logging.getLogger("gacha-bot")


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


# ================================================================
# 热键字符串 → pynput Key 映射
# ================================================================

def _str_to_key(s: str) -> Key | str:
    """将 'f6' 转为 Key.f6, 'esc' 转为 Key.esc"""
    mapping = {
        "f1": Key.f1, "f2": Key.f2, "f3": Key.f3, "f4": Key.f4,
        "f5": Key.f5, "f6": Key.f6, "f7": Key.f7, "f8": Key.f8,
        "f9": Key.f9, "f10": Key.f10, "f11": Key.f11, "f12": Key.f12,
        "esc": Key.esc, "enter": Key.enter, "space": Key.space,
        "tab": Key.tab, "shift": Key.shift, "ctrl": Key.ctrl,
        "alt": Key.alt, "pause": Key.pause, "print_screen": Key.print_screen,
    }
    return mapping.get(s.lower(), s)


# ================================================================
# 模板截取工具
# ================================================================

def cmd_capture(name: str, region: tuple[int, int, int, int] | None = None) -> None:
    """截取屏幕区域保存为模板图片"""
    TEMPLATE_DIR.mkdir(exist_ok=True)

    if region is None:
        print("请在 3 秒内将鼠标移到目标按钮的【左上角】...")
        time.sleep(3)
        x1, y1 = pyautogui.position()
        print(f"左上角坐标: ({x1}, {y1})")

        print("现在将鼠标移到目标按钮的【右下角】...")
        time.sleep(3)
        x2, y2 = pyautogui.position()
        print(f"右下角坐标: ({x2}, {y2})")
    else:
        x1, y1, x2, y2 = region

    left, top = min(x1, x2), min(y1, y2)
    width, height = abs(x2 - x1), abs(y2 - y1)

    if width < 5 or height < 5:
        print(f"错误: 选区太小 ({width}x{height})，请重新选择")
        sys.exit(1)

    screenshot = pyautogui.screenshot(region=(left, top, width, height))
    filepath = TEMPLATE_DIR / name
    screenshot.save(str(filepath))
    print(f"模板已保存: {filepath}  ({width}x{height})")


# ================================================================
# 运行模式
# ================================================================

def cmd_run() -> None:
    """启动抽卡机器人"""
    region = {"x1": 0, "y1": 0, "x2": 0, "y2": 0, "ready": False}

    print("=" * 50)
    print("  战火英雄自动抽卡  -- by chuqing")
    print("  建议游戏 1280x720 左右窗口化运行")
    print(f"  F9=左上角  |  F10=右下角  |  两个都设好才能启动")
    print(f"  启动: {START_KEY.upper()}  |  停止: {STOP_KEY.upper()}  |  退出: {EXIT_KEY.upper()}")
    print("=" * 50)

    bot = GachaBot()
    flag = {"bot_active": False, "program_active": True}

    start_key = _str_to_key(START_KEY)
    stop_key = _str_to_key(STOP_KEY)
    exit_key = _str_to_key(EXIT_KEY)
    p1_key = _str_to_key("f9")
    p2_key = _str_to_key("f10")

    def _apply_region() -> None:
        left = min(region["x1"], region["x2"])
        top = min(region["y1"], region["y2"])
        w = abs(region["x2"] - region["x1"])
        h = abs(region["y2"] - region["y1"])
        bot.set_capture_region((left, top, w, h))
        print(f">>> 截图区域已设置: ({left}, {top}, {w}, {h})")

    def on_press(key: Key | str) -> None:
        nonlocal region
        if key == start_key:
            if not region["ready"]:
                print("\n>>> 请先按 F9(左上角) 和 F10(右下角) 设置游戏窗口区域！")
                return
            if not flag["bot_active"]:
                flag["bot_active"] = True
                print("\n>>> 机器人开始运行...")
            else:
                print("机器人已在运行中")
        elif key == stop_key:
            if flag["bot_active"]:
                flag["bot_active"] = False
                print(f"\n>>> 机器人已暂停，按 {START_KEY.upper()} 继续")
        elif key == exit_key:
            flag["bot_active"] = False
            flag["program_active"] = False
            print("\n>>> 退出程序...")
        elif key == p1_key:
            x, y = pyautogui.position()
            region["x1"], region["y1"] = x, y
            print(f"\n>>> 坐标1 (左上): ({x}, {y})")
            if region["x2"] != 0 or region["y2"] != 0:
                region["ready"] = True
                _apply_region()
            else:
                _print_region_hint()
        elif key == p2_key:
            x, y = pyautogui.position()
            region["x2"], region["y2"] = x, y
            print(f"\n>>> 坐标2 (右下): ({x}, {y})")
            if region["x1"] != 0 or region["y1"] != 0:
                region["ready"] = True
                _apply_region()
            else:
                _print_region_hint()

    listener = Listener(on_press=on_press)
    listener.start()

    print(">>> 请设置游戏窗口区域:")
    print("    1. 鼠标移到游戏窗口 左上角 → 按 F9")
    print("    2. 鼠标移到游戏窗口 右下角 → 按 F10")
    print("    3. 设置完成后按 F6 启动")

    try:
        while flag["program_active"]:
            if flag["bot_active"]:
                acted = bot.step()
                if not acted:
                    time.sleep(0.5)
            else:
                time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        listener.stop()
        print("程序已退出")


def _print_region_hint() -> None:
    print("  请按另一个坐标键 (F9/F10) 完成区域设置")


# ================================================================
# 预览模式：实时显示匹配状态，不实际点击
# ================================================================

def cmd_preview() -> None:
    """预览模式：显示截图和模板匹配结果，不执行点击，用于调试"""
    from config import CAPTURE_REGION, MATCH_THRESHOLD, STATES

    bot = GachaBot()
    flag = {"running": True, "region_ready": CAPTURE_REGION is not None}
    region = {"x1": 0, "y1": 0, "x2": 0, "y2": 0}

    if flag["region_ready"]:
        print(f"截图区域: {CAPTURE_REGION}")
    else:
        print("=" * 50)
        print("  请先设置游戏窗口区域！")
        print("  1. 鼠标移到游戏窗口 左上角 → 按 F9")
        print("  2. 鼠标移到游戏窗口 右下角 → 按 F10")
        print("  设置完成后预览窗口自动打开")
        print("=" * 50)

    def _apply_region() -> None:
        left = min(region["x1"], region["x2"])
        top = min(region["y1"], region["y2"])
        w = abs(region["x2"] - region["x1"])
        h = abs(region["y2"] - region["y1"])
        bot.set_capture_region((left, top, w, h))
        flag["region_ready"] = True
        print(f"\n>>> 截图区域已应用: ({left}, {top}, {w}, {h})")
        print(f">>> 复制到 config.py: CAPTURE_REGION = ({left}, {top}, {w}, {h})")

    def on_press(key: Key | str) -> None:
        if key == _str_to_key("f9"):
            x, y = pyautogui.position()
            region["x1"], region["y1"] = x, y
            print(f">>> 坐标1 (左上): ({x}, {y})")
            if region["x2"] != 0 or region["y2"] != 0:
                _apply_region()
            else:
                _print_region_hint()
        elif key == _str_to_key("f10"):
            x, y = pyautogui.position()
            region["x2"], region["y2"] = x, y
            print(f">>> 坐标2 (右下): ({x}, {y})")
            if region["x1"] != 0 or region["y1"] != 0:
                _apply_region()
            else:
                _print_region_hint()
        elif key == _str_to_key("esc"):
            if not flag["region_ready"]:
                return
            states = list(STATES.keys())
            idx = states.index(bot.state)
            bot._state = states[(idx + 1) % len(states)]
            print(f"\n>>> 切换状态: {bot.state}")
        elif hasattr(key, 'char') and key.char == 'q':
            flag["running"] = False

    listener = Listener(on_press=on_press)
    listener.start()

    # 等待区域设置完成
    while flag["running"] and not flag["region_ready"]:
        time.sleep(0.1)

    if not flag["running"]:
        listener.stop()
        return

    print(f"\n状态机: {len(STATES)} 个状态")
    for state, rules in STATES.items():
        print(f"  [{state}]: {[r['template'] for r in rules]}")
    print("  Q=退出  |  ESC=切换状态")
    print("  预览窗口已打开（右下角）\n")

    win_name = "Preview (Q=quit, ESC=next state)"
    cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win_name, 480, 270)
    cv2.moveWindow(win_name, 1440, 810)

    try:
        while flag["running"]:
            screenshot = bot.capture()
            display = screenshot.copy()

            rules = STATES.get(bot.state, [])
            for rule in rules:
                template = rule["template"]
                if template == "__always__":
                    continue

                tpl = bot._templates.get(template)
                th, tw = tpl.shape[:2]

                result = cv2.matchTemplate(screenshot, tpl, bot._match_method)
                _, max_val, _, max_loc = cv2.minMaxLoc(result)

                if bot._match_method in (cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED):
                    matched = max_val <= (1.0 - MATCH_THRESHOLD)
                else:
                    matched = max_val >= MATCH_THRESHOLD

                color = (0, 255, 0) if matched else (0, 0, 255)
                cv2.rectangle(display, max_loc, (max_loc[0] + tw, max_loc[1] + th), color, 2)
                label = f"{template} ({max_val:.2f})"
                cv2.putText(display, label, (max_loc[0], max_loc[1] - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

                click_target = rule.get("click_target")
                if click_target:
                    ct_tpl = bot._templates.get(click_target)
                    ct_h, ct_w = ct_tpl.shape[:2]
                    ct_result = cv2.matchTemplate(screenshot, ct_tpl, bot._match_method)
                    _, ct_max_val, _, ct_max_loc = cv2.minMaxLoc(ct_result)
                    ct_color = (255, 255, 0)
                    cv2.rectangle(display, ct_max_loc, (ct_max_loc[0] + ct_w, ct_max_loc[1] + ct_h), ct_color, 2)
                    ct_label = f"click-> {click_target} ({ct_max_val:.2f})"
                    cv2.putText(display, ct_label, (ct_max_loc[0], ct_max_loc[1] - 5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, ct_color, 1)

            cv2.putText(display, f"State: {bot.state}  |  Cycle: {bot._cycles}", (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

            cv2.imshow(win_name, display)

            if cv2.waitKey(33) & 0xFF == ord("q"):
                break

    finally:
        flag["running"] = False
        listener.stop()
        cv2.destroyAllWindows()


# ================================================================
# CLI
# ================================================================

def main() -> None:
    parser = argparse.ArgumentParser(description="自动化抽卡机器人")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("run", help="启动抽卡机器人")
    sub.add_parser("preview", help="预览模式：显示匹配结果，不点击")

    cap = sub.add_parser("capture", help="截取模板图片")
    cap.add_argument("name", help="模板文件名 (如 roll.png)")
    cap.add_argument("--x1", type=int, help="左上角 X")
    cap.add_argument("--y1", type=int, help="左上角 Y")
    cap.add_argument("--x2", type=int, help="右下角 X")
    cap.add_argument("--y2", type=int, help="右下角 Y")

    sub.add_parser("list", help="列出所有模板文件")

    args = parser.parse_args()

    if args.command == "run":
        setup_logging(LOG_LEVEL)
        cmd_run()

    elif args.command == "preview":
        setup_logging("DEBUG")
        cmd_preview()

    elif args.command == "capture":
        region = None
        if all(v is not None for v in [args.x1, args.y1, args.x2, args.y2]):
            region = (args.x1, args.y1, args.x2, args.y2)
        cmd_capture(args.name, region)

    elif args.command == "list":
        templates = sorted(TEMPLATE_DIR.glob("*.png"))
        if templates:
            print("已保存的模板:")
            for t in templates:
                size = t.stat().st_size
                print(f"  {t.name}  ({size / 1024:.1f} KB)")
        else:
            print("尚无模板文件，使用 'python main.py capture <名称>' 创建")

    else:
        if getattr(sys, 'frozen', False):
            # 双击 exe 时显示交互菜单
            _interactive_menu()
        else:
            parser.print_help()


def _interactive_menu() -> None:
    """双击 exe 无参数时的交互菜单"""
    import msvcrt

    while True:
        print()
        print("=" * 40)
        print("  战火英雄自动抽卡  -- by chuqing")
        print("=" * 40)
        print("  建议游戏 1280x720 左右窗口化运行")
        print("  使用 F9/F10 定位游戏窗口区域，同时请打开军械商店后再继续本程序")
        print("  本程序自动抽卡并保留黄黄黄黄，黄黄黄蓝，黄黄黄绿三种武器")
        print("  注意准备足够的钱（bushi")
        print("-" * 40)
        print("  1. 运行机器人 (run)")
        print("  2. 预览模式 (preview)")
        print("  3. 截取模板 (capture)")
        print("  4. 模板列表 (list)")
        print("  0. 退出")
        print("=" * 40)
        print("  请选择 (0-4): ", end="", flush=True)

        try:
            ch = msvcrt.getch().decode("utf-8").strip()
        except UnicodeDecodeError:
            ch = ""

        print(ch)
        print()

        if ch == "1":
            setup_logging(LOG_LEVEL)
            cmd_run()
        elif ch == "2":
            setup_logging("DEBUG")
            cmd_preview()
        elif ch == "3":
            name = input("模板文件名 (如 test.png): ").strip()
            if name:
                cmd_capture(name)
        elif ch == "4":
            templates = sorted(TEMPLATE_DIR.glob("*.png"))
            if templates:
                print("已保存的模板:")
                for t in templates:
                    size = t.stat().st_size
                    print(f"  {t.name}  ({size / 1024:.1f} KB)")
            else:
                print("尚无模板文件")
            input("按回车继续...")
        elif ch == "0":
            break
        else:
            print("无效选择，请重新输入")


if __name__ == "__main__":
    main()
