"""本地 Mock 参考示例：观察消息和工具调用。"""

import argparse
import json

from .agent import Agent
from .runtime import RuntimeEvent, RunStatus


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("message", nargs="?", help="单次运行，例如 'add 2 3'")
    parser.add_argument("--trace", action="store_true", help="显示每一步的运行时事件")
    parser.add_argument("--max-steps", type=int, default=10)
    args = parser.parse_args()

    def show_event(event: RuntimeEvent) -> None:
        print(f"[{event.step}] {event.kind}: {json.dumps(event.data, ensure_ascii=False)}")

    agent = Agent(
        max_steps=args.max_steps,
        on_event=show_event if args.trace else None,
    )
    if args.message is not None:
        result = agent.run(args.message)
        print(result.content if result.status is RunStatus.COMPLETED else result.error)
        return 0 if result.status is RunStatus.COMPLETED else 1

    print("本地 Mock：输入 add 2 3 观察工具调用")
    print("/clear 清空历史，/history 查看消息，/quit 退出")
    while True:
        try:
            text = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if text == "/quit":
            return 0
        if text == "/clear":
            agent.reset()
        elif text == "/history":
            print(json.dumps(agent.messages, ensure_ascii=False, indent=2))
        elif text:
            print(agent.chat(text))


if __name__ == "__main__":
    raise SystemExit(main())
