# 程序入口
from agent import ChatAgent


# ── 特殊指令 ──
EXIT_COMMANDS  = {"quit", "exit", "退出", "q"}
RESET_COMMANDS = {"clear", "reset", "清空", "新对话"}
HELP_COMMANDS  = {"help", "帮助", "?"}

HELP_TEXT = """
可用指令：
  quit / 退出    — 结束程序
  clear / 清空   — 清空对话历史，开始新对话
  help / 帮助    — 显示此帮助
"""


def run() -> None:
    print("=" * 48)
    print("    离散数学智能助教  v0.1  (纯对话版)")
    print("=" * 48)
    print('输入 "help" 查看可用指令\n')

    agent = ChatAgent()

    while True:
        try:
            user_input = input("你：").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n再见！")
            break

        # 空输入跳过
        if not user_input:
            continue

        # 处理特殊指令
        cmd = user_input.lower()
        if cmd in EXIT_COMMANDS:
            print("再见！有问题随时来找我～")
            break
        if cmd in RESET_COMMANDS:
            agent.reset()
            continue
        if cmd in HELP_COMMANDS:
            print(HELP_TEXT)
            continue

        # 正常对话
        try:
            print("助教：思考中...", end="\r")  # 显示等待提示
            reply = agent.chat(user_input)
            print(f"助教：{reply}\n")
        except Exception as e:
            print(f"\n[错误] 请求失败：{e}")
            print("请检查网络连接和 API Key 是否正确。\n")

if __name__ == "__main__":
    run()