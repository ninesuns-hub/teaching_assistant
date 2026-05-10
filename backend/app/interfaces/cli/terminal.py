from app.core.agent import ChatAgent

def run_cli():
    print("=" * 48)
    print("    离散数学智能助教 (CLI)")
    print("=" * 48)
    print('输入 "exit" 退出，"clear" 重置对话\n')

    agent = ChatAgent()

    while True:
        try:
            user_input = input("你：").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if not user_input: continue
        if user_input.lower() in ["exit", "quit", "退出"]: break
        if user_input.lower() in ["clear", "reset", "清空"]:
            agent.reset()
            print("对话已重置。")
            continue

        try:
            print("助教：思考中...", end="\r")
            reply = agent.chat(user_input)
            print(f"助教：{reply}\n")
        except Exception as e:
            print(f"\n[错误] {e}\n")
