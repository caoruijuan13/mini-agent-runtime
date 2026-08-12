"""
mini-agent — A colorful terminal chat interface for the AI agent.

Usage:
    python -m agent
    python -m agent --server http://localhost:3000
    python -m agent --no-stream
"""

import argparse
import sys
import time

from .agent import Agent
from .tools import create_default_registry


# ─── Terminal Colors ──────────────────────────────────────────────────────────

class Colors:
    """ANSI color codes for terminal output."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"

    # Foreground colors
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    GRAY = "\033[90m"

    # Background colors
    BG_BLUE = "\033[44m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_MAGENTA = "\033[45m"


def colored(text: str, *styles: str) -> str:
    """Apply ANSI styles to text."""
    return "".join(styles) + text + Colors.RESET


def print_banner():
    """Print the startup banner."""
    banner = f"""
{colored('╔══════════════════════════════════════════════════╗', Colors.CYAN)}
{colored('║', Colors.CYAN)}  {colored('🤖 mini-agent', Colors.BOLD + Colors.WHITE)}                              {colored('║', Colors.CYAN)}
{colored('║', Colors.CYAN)}  {colored('A lightweight AI Agent runtime', Colors.GRAY)}           {colored('║', Colors.CYAN)}
{colored('╚══════════════════════════════════════════════════╝', Colors.CYAN)}
"""
    print(banner)


def print_help():
    """Print available commands."""
    print(colored("\n📖 可用命令:", Colors.YELLOW + Colors.BOLD))
    print(colored("  /help     ", Colors.CYAN) + "显示此帮助信息")
    print(colored("  /tools    ", Colors.CYAN) + "列出可用工具")
    print(colored("  /clear    ", Colors.CYAN) + "清除对话历史")
    print(colored("  /history  ", Colors.CYAN) + "显示对话历史")
    print(colored("  /quit     ", Colors.CYAN) + "退出程序")
    print(colored("  /exit     ", Colors.CYAN) + "退出程序")
    print()
    print(colored("💡 直接输入消息与 Agent 对话，例如:", Colors.GRAY))
    print(colored('   "你好"           ', Colors.GREEN) + "— 打招呼")
    print(colored('   "北京天气怎么样"  ', Colors.GREEN) + "— 查天气")
    print(colored('   "计算 123 * 456" ', Colors.GREEN) + "— 做计算")
    print(colored('   "现在几点"       ', Colors.GREEN) + "— 查时间")
    print(colored('   "翻译: 你好"     ', Colors.GREEN) + "— 翻译文本")
    print()


def print_tools(tools):
    """Display available tools."""
    print(colored("\n🔧 可用工具:", Colors.MAGENTA + Colors.BOLD))
    for tool in tools:
        print(colored(f"  • {tool['name']}", Colors.CYAN + Colors.BOLD))
        print(colored(f"    {tool['description']}", Colors.GRAY))
    print()


def print_history(messages):
    """Display conversation history."""
    print(colored("\n📜 对话历史:", Colors.BLUE + Colors.BOLD))
    print(colored("─" * 50, Colors.GRAY))
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        if role == "system":
            continue
        elif role == "user":
            print(colored(f"  👤 You: ", Colors.GREEN + Colors.BOLD) + (content or ""))
        elif role == "assistant":
            print(colored(f"  🤖 Agent: ", Colors.CYAN + Colors.BOLD) + (content or ""))
        elif role == "tool":
            name = msg.get("name", "unknown")
            print(colored(f"  🔧 Tool({name}): ", Colors.YELLOW) + (content or "")[:100] + "...")
    print(colored("─" * 50, Colors.GRAY))
    print()


def create_agent(server_url: str, stream: bool = True) -> Agent:
    """Create and configure the agent with display callbacks."""

    def on_tool_call(name: str, args: dict):
        args_str = ", ".join(f"{k}={v!r}" for k, v in args.items())
        print(colored(f"\n  🔧 调用工具: {name}({args_str})", Colors.YELLOW + Colors.ITALIC))

    def on_tool_result(name: str, result: str):
        lines = result.split("\n")
        print(colored(f"  ✅ 工具结果 [{name}]:", Colors.GREEN))
        for line in lines:
            print(colored(f"     {line}", Colors.GRAY))

    def on_stream_chunk(chunk: str):
        print(chunk, end="", flush=True)

    return Agent(
        server_url=server_url,
        tool_registry=create_default_registry(),
        on_tool_call=on_tool_call,
        on_tool_result=on_tool_result,
        on_stream_chunk=on_stream_chunk if stream else None,
    )


def main():
    """Main entry point for the chat interface."""
    parser = argparse.ArgumentParser(description="mini-agent chat interface")
    parser.add_argument(
        "--server", "-s",
        default="http://127.0.0.1:3000",
        help="Server URL (default: http://127.0.0.1:3000)",
    )
    parser.add_argument(
        "--no-stream",
        action="store_true",
        help="Disable streaming output",
    )
    args = parser.parse_args()

    stream = not args.no_stream

    # Print banner
    print_banner()

    # Create agent
    agent = create_agent(args.server, stream=stream)

    # Check server connection
    print(colored("  连接服务器...", Colors.GRAY), end="", flush=True)
    if agent.client.is_server_running():
        health = agent.client.health()
        print(colored(f" ✅ 已连接", Colors.GREEN))
        print(colored(f"  服务器版本: {health.get('version', '?')}  |  "
                       f"LLM: {health.get('llm_provider', '?')}  |  "
                       f"工具: {health.get('tools_count', 0)} 个", Colors.GRAY))
    else:
        print(colored(f" ❌ 无法连接到 {args.server}", Colors.RED))
        print(colored("  请先启动 Rust 服务端: cargo run", Colors.YELLOW))
        sys.exit(1)

    # Show tools
    tools_info = agent.tools.list_tools()
    print_tools(tools_info)

    # Welcome message
    print(colored("─" * 50, Colors.GRAY))
    print(colored("  输入 /help 查看命令  |  输入 /quit 退出", Colors.GRAY))
    print(colored("─" * 50, Colors.GRAY))
    print()

    # Main chat loop
    while True:
        try:
            # Get user input
            user_input = input(colored("  👤 You › ", Colors.GREEN + Colors.BOLD)).strip()

            if not user_input:
                continue

            # Handle commands
            if user_input.startswith("/"):
                cmd = user_input.lower().split()[0]
                if cmd in ("/quit", "/exit", "/q"):
                    print(colored("\n  👋 再见！感谢使用 mini-agent。\n", Colors.CYAN))
                    break
                elif cmd == "/help":
                    print_help()
                    continue
                elif cmd == "/tools":
                    print_tools(agent.tools.list_tools())
                    continue
                elif cmd == "/clear":
                    agent.reset()
                    print(colored("  🗑️  对话历史已清除。\n", Colors.YELLOW))
                    continue
                elif cmd == "/history":
                    print_history(agent.messages)
                    continue
                else:
                    print(colored(f"  ❓ 未知命令: {cmd}  (输入 /help 查看可用命令)", Colors.RED))
                    continue

            # Process message through agent
            print()  # blank line before response

            if stream:
                print(colored("  🤖 Agent › ", Colors.CYAN + Colors.BOLD), end="", flush=True)
                response = agent.chat_stream(user_input)
                print()  # newline after streaming
            else:
                response = agent.chat(user_input)
                # Display response
                print(colored("  🤖 Agent › ", Colors.CYAN + Colors.BOLD))
                for line in response.split("\n"):
                    print(colored("  ", Colors.CYAN) + line)

            print()  # blank line after response

        except KeyboardInterrupt:
            print(colored("\n\n  👋 再见！\n", Colors.CYAN))
            break
        except EOFError:
            print(colored("\n\n  👋 再见！\n", Colors.CYAN))
            break
        except Exception as e:
            print(colored(f"\n  ❌ 错误: {e}\n", Colors.RED))
            continue


if __name__ == "__main__":
    main()
