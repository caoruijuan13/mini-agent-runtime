# 快速开始

## 环境要求

- Rust 1.70 或更高版本。
- Python 3.10 或更高版本。
- `pip`。
- 真实模型模式还需要兼容 OpenAI Chat Completions 的服务和 API Key。

## Mock 模式

Mock 模式不访问外部模型，适合验证启动、Agent 循环和工具调用。

```bash
python3 -m pip install -r python/requirements.txt
bash scripts/run_demo.sh
```

脚本会构建 Rust release 二进制、启动 `127.0.0.1:3000` 服务，然后进入 Python 终端。

常用终端命令：

| 命令 | 作用 |
| --- | --- |
| `/help` | 显示帮助 |
| `/tools` | 显示本地工具 |
| `/history` | 显示当前对话历史 |
| `/clear` | 清空对话历史 |
| `/quit` | 退出 |

## 分别启动服务和 Agent

终端一：

```bash
LLM_PROVIDER=mock cargo run
```

终端二：

```bash
cd python
python3 -m agent --server http://127.0.0.1:3000
```

服务就绪后可以验证健康状态：

```bash
curl http://127.0.0.1:3000/health
```

## 接入真实模型

```bash
cp .env.example .env
```

至少配置：

```dotenv
LLM_PROVIDER=openai
OPENAI_API_KEY=replace-me
OPENAI_BASE_URL=https://api.openai.com/v1
MODEL=gpt-4o-mini
```

`LLM_PROVIDER=openai` 表示走 OpenAI 兼容协议，并不限制后端厂商。配置完成后运行：

```bash
cargo run
```

!!! warning "密钥"
    `.env` 已被 Git 忽略。不要把真实 API Key 写入文档、测试、日志或提交记录。

## Docker

只运行服务：

```bash
docker build -t mini-agent-runtime .
docker run --rm -p 3000:3000 -e LLM_PROVIDER=mock mini-agent-runtime
```

运行 Compose：

```bash
docker compose up --build
```

Compose 中的 Agent 使用交互终端；自动化环境通常只启动 `server` 服务。

## 下一步

- 环境变量说明见[配置说明](configuration.md)。
- 请求格式见[服务接口](server-api.md)。
- 首次修改代码前先运行[确定性 QA](quality.md)。
