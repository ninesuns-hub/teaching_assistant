import sys
import argparse
from app.interfaces.cli.terminal import run_cli

def main():
    parser = argparse.ArgumentParser(description="Discrete Math Tutor")
    parser.add_argument("--mode", choices=["cli", "api"], default="cli", help="运行模式")
    args = parser.parse_args()

    if args.mode == "cli":
        run_cli()
    else:
        print("请运行 server.py 启动 API 服务。")

if __name__ == "__main__":
    main()
