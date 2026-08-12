use crate::config::Config;
use crate::tools::ToolRegistry;
use futures::Stream;
use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::pin::Pin;
use tracing::{debug, info};

/// A chat message in the conversation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatMessage {
    pub role: String,
    #[serde(default)]
    pub content: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tool_calls: Option<Vec<LlmToolCall>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tool_call_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,
}

/// Tool call as returned by the LLM API.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LlmToolCall {
    pub id: String,
    pub r#type: String,
    pub function: LlmFunctionCall,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LlmFunctionCall {
    pub name: String,
    pub arguments: String,
}

/// The response from the LLM.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LlmResponse {
    pub content: Option<String>,
    pub tool_calls: Option<Vec<LlmToolCall>>,
    pub finish_reason: String,
    pub usage: Option<UsageInfo>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UsageInfo {
    pub prompt_tokens: u32,
    pub completion_tokens: u32,
    pub total_tokens: u32,
}

/// A single SSE chunk from streaming response.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StreamChunk {
    pub delta_content: Option<String>,
    pub delta_tool_calls: Option<Vec<LlmToolCall>>,
    pub finish_reason: Option<String>,
}

/// LLM client that supports both real API and mock mode.
pub struct LlmClient {
    config: Config,
    http: Client,
}

impl LlmClient {
    pub fn new(config: Config) -> Self {
        Self {
            config,
            http: Client::new(),
        }
    }

    /// Send a chat completion request (non-streaming).
    pub async fn chat(
        &self,
        messages: &[ChatMessage],
        tools: &ToolRegistry,
    ) -> Result<LlmResponse, String> {
        if self.config.is_mock() {
            return Ok(self.mock_response(messages, tools));
        }
        self.openai_chat(messages, tools, false)
            .await
            .map(|r| r.0)
    }

    /// Send a chat completion request (streaming) — returns a stream of chunks.
    pub async fn chat_stream(
        &self,
        messages: &[ChatMessage],
        tools: &ToolRegistry,
    ) -> Result<Pin<Box<dyn Stream<Item = StreamChunk> + Send>>, String> {
        if self.config.is_mock() {
            return Ok(self.mock_stream(messages));
        }
        self.openai_stream(messages, tools).await
    }

    /// Call OpenAI-compatible chat completions API (non-streaming).
    async fn openai_chat(
        &self,
        messages: &[ChatMessage],
        tools: &ToolRegistry,
        _stream: bool,
    ) -> Result<(LlmResponse, Option<reqwest::Response>), String> {
        let url = format!(
            "{}/chat/completions",
            self.config.openai_base_url.trim_end_matches('/')
        );

        let mut body = serde_json::json!({
            "model": self.config.model,
            "messages": messages,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "stream": false,
        });

        let tool_defs = tools.to_openai_tools();
        if !tool_defs.is_empty() {
            body["tools"] = serde_json::Value::Array(
                tool_defs.into_iter().map(|v| v).collect(),
            );
            // "auto" lets the model decide whether to call a tool
            body["tool_choice"] = serde_json::json!("auto");
        }

        debug!("LLM request: {}", serde_json::to_string_pretty(&body).unwrap_or_default());

        let resp = self
            .http
            .post(&url)
            .header("Authorization", format!("Bearer {}", self.config.openai_api_key))
            .header("Content-Type", "application/json")
            .json(&body)
            .send()
            .await
            .map_err(|e| format!("HTTP request failed: {e}"))?;

        if !resp.status().is_success() {
            let status = resp.status();
            let text = resp.text().await.unwrap_or_default();
            return Err(format!("LLM API error {status}: {text}"));
        }

        let json: serde_json::Value = resp
            .json()
            .await
            .map_err(|e| format!("Failed to parse LLM response: {e}"))?;

        debug!("LLM response: {}", serde_json::to_string_pretty(&json).unwrap_or_default());

        let choice = json["choices"]
            .as_array()
            .and_then(|a| a.first())
            .ok_or_else(|| "No choices in LLM response".to_string())?;

        let message = &choice["message"];

        let content = message["content"].as_str().map(|s| s.to_string());

        let tool_calls = message["tool_calls"]
            .as_array()
            .map(|calls| {
                calls
                    .iter()
                    .filter_map(|c| {
                        serde_json::from_value(c.clone()).ok()
                    })
                    .collect()
            });

        let finish_reason = choice["finish_reason"]
            .as_str()
            .unwrap_or("stop")
            .to_string();

        let usage = json["usage"].as_object().map(|u| UsageInfo {
            prompt_tokens: u["prompt_tokens"].as_u64().unwrap_or(0) as u32,
            completion_tokens: u["completion_tokens"].as_u64().unwrap_or(0) as u32,
            total_tokens: u["total_tokens"].as_u64().unwrap_or(0) as u32,
        });

        info!(
            finish_reason = %finish_reason,
            has_tool_calls = tool_calls.is_some(),
            "LLM response received"
        );

        Ok((
            LlmResponse {
                content,
                tool_calls,
                finish_reason,
                usage,
            },
            None,
        ))
    }

    /// Call OpenAI-compatible API with streaming.
    async fn openai_stream(
        &self,
        messages: &[ChatMessage],
        tools: &ToolRegistry,
    ) -> Result<Pin<Box<dyn Stream<Item = StreamChunk> + Send>>, String> {
        let url = format!(
            "{}/chat/completions",
            self.config.openai_base_url.trim_end_matches('/')
        );

        let mut body = serde_json::json!({
            "model": self.config.model,
            "messages": messages,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "stream": true,
        });

        let tool_defs = tools.to_openai_tools();
        if !tool_defs.is_empty() {
            body["tools"] = serde_json::Value::Array(
                tool_defs.into_iter().map(|v| v).collect(),
            );
            body["tool_choice"] = serde_json::json!("auto");
        }

        let resp = self
            .http
            .post(&url)
            .header("Authorization", format!("Bearer {}", self.config.openai_api_key))
            .header("Content-Type", "application/json")
            .json(&body)
            .send()
            .await
            .map_err(|e| format!("HTTP request failed: {e}"))?;

        if !resp.status().is_success() {
            let status = resp.status();
            let text = resp.text().await.unwrap_or_default();
            return Err(format!("LLM API error {status}: {text}"));
        }

        let byte_stream = resp.bytes_stream();

        let stream = futures::stream::unfold(
            (byte_stream, String::new()),
            |(mut byte_stream, mut buffer)| async move {
                use futures::StreamExt;
                while let Some(chunk_result) = byte_stream.next().await {
                    match chunk_result {
                        Ok(bytes) => {
                            buffer.push_str(&String::from_utf8_lossy(&bytes));
                            // Process complete lines
                            while let Some(newline_pos) = buffer.find('\n') {
                                let line = buffer[..newline_pos].trim().to_string();
                                buffer = buffer[newline_pos + 1..].to_string();

                                if line.is_empty() || line == "data: [DONE]" {
                                    continue;
                                }
                                if let Some(data) = line.strip_prefix("data: ") {
                                    if let Ok(json) = serde_json::from_str::<serde_json::Value>(data) {
                                        if let Some(choice) = json["choices"].as_array().and_then(|a| a.first()) {
                                            let delta = &choice["delta"];
                                            let chunk = StreamChunk {
                                                delta_content: delta["content"].as_str().map(|s| s.to_string()),
                                                delta_tool_calls: None,
                                                finish_reason: choice["finish_reason"].as_str().map(|s| s.to_string()),
                                            };
                                            return Some((chunk, (byte_stream, buffer)));
                                        }
                                    }
                                }
                            }
                        }
                        Err(_) => break,
                    }
                }
                None
            },
        );

        Ok(Box::pin(stream))
    }

    /// Generate a mock response for testing without a real LLM.
    fn mock_response(&self, messages: &[ChatMessage], _tools: &ToolRegistry) -> LlmResponse {
        let last_user_msg = messages
            .iter()
            .rev()
            .find(|m| m.role == "user")
            .and_then(|m| m.content.as_deref())
            .unwrap_or("");

        info!(msg = %last_user_msg, "Generating mock response");

        // Simple pattern matching to demonstrate tool calling
        let lower = last_user_msg.to_lowercase();

        if lower.contains("weather") || lower.contains("天气") {
            // Extract city name (simple heuristic)
            let city = extract_city_name(last_user_msg);
            let tool_id = format!("call_{}", uuid::Uuid::new_v4().to_string().replace('-', "")[..24].to_string());

            LlmResponse {
                content: None,
                tool_calls: Some(vec![LlmToolCall {
                    id: tool_id,
                    r#type: "function".to_string(),
                    function: LlmFunctionCall {
                        name: "get_weather".to_string(),
                        arguments: serde_json::json!({"city": city, "unit": "celsius"}).to_string(),
                    },
                }]),
                finish_reason: "tool_calls".to_string(),
                usage: Some(UsageInfo {
                    prompt_tokens: 50,
                    completion_tokens: 20,
                    total_tokens: 70,
                }),
            }
        } else if lower.contains("calculate") || lower.contains("计算") || lower.contains("多少") {
            let tool_id = format!("call_{}", uuid::Uuid::new_v4().to_string().replace('-', "")[..24].to_string());

            LlmResponse {
                content: None,
                tool_calls: Some(vec![LlmToolCall {
                    id: tool_id,
                    r#type: "function".to_string(),
                    function: LlmFunctionCall {
                        name: "calculate".to_string(),
                        arguments: serde_json::json!({"expression": "2 + 2"}).to_string(),
                    },
                }]),
                finish_reason: "tool_calls".to_string(),
                usage: Some(UsageInfo {
                    prompt_tokens: 45,
                    completion_tokens: 18,
                    total_tokens: 63,
                }),
            }
        } else if lower.contains("time") || lower.contains("时间") || lower.contains("几点") {
            let tool_id = format!("call_{}", uuid::Uuid::new_v4().to_string().replace('-', "")[..24].to_string());

            LlmResponse {
                content: None,
                tool_calls: Some(vec![LlmToolCall {
                    id: tool_id,
                    r#type: "function".to_string(),
                    function: LlmFunctionCall {
                        name: "get_current_time".to_string(),
                        arguments: serde_json::json!({"timezone": "Asia/Shanghai"}).to_string(),
                    },
                }]),
                finish_reason: "tool_calls".to_string(),
                usage: Some(UsageInfo {
                    prompt_tokens: 40,
                    completion_tokens: 15,
                    total_tokens: 55,
                }),
            }
        } else if lower.contains("translate") || lower.contains("翻译") {
            let tool_id = format!("call_{}", uuid::Uuid::new_v4().to_string().replace('-', "")[..24].to_string());

            LlmResponse {
                content: None,
                tool_calls: Some(vec![LlmToolCall {
                    id: tool_id,
                    r#type: "function".to_string(),
                    function: LlmFunctionCall {
                        name: "translate".to_string(),
                        arguments: serde_json::json!({
                            "text": last_user_msg,
                            "target_language": "English",
                        }).to_string(),
                    },
                }]),
                finish_reason: "tool_calls".to_string(),
                usage: Some(UsageInfo {
                    prompt_tokens: 55,
                    completion_tokens: 25,
                    total_tokens: 80,
                }),
            }
        } else if lower.contains("search") || lower.contains("搜索") || lower.contains("查找") {
            let tool_id = format!("call_{}", uuid::Uuid::new_v4().to_string().replace('-', "")[..24].to_string());

            LlmResponse {
                content: None,
                tool_calls: Some(vec![LlmToolCall {
                    id: tool_id,
                    r#type: "function".to_string(),
                    function: LlmFunctionCall {
                        name: "search_knowledge".to_string(),
                        arguments: serde_json::json!({"query": last_user_msg, "max_results": 3}).to_string(),
                    },
                }]),
                finish_reason: "tool_calls".to_string(),
                usage: Some(UsageInfo {
                    prompt_tokens: 48,
                    completion_tokens: 22,
                    total_tokens: 70,
                }),
            }
        } else {
            // Regular chat response
            let reply = if lower.contains("hello") || lower.contains("你好") || lower.contains("hi") {
                "你好！我是 mini-agent，一个轻量级的 AI 助手。我可以帮你查天气、做计算、查时间、翻译文本等。有什么需要帮忙的吗？".to_string()
            } else if lower.contains("help") || lower.contains("帮助") {
                "我可以帮你完成以下任务：\n\n🌤️ **查天气** — 例如：\"北京今天天气怎么样？\"\n🧮 **做计算** — 例如：\"帮我计算 123 * 456\"\n🕐 **查时间** — 例如：\"现在纽约几点？\"\n🌐 **翻译** — 例如：\"翻译：Hello World 到中文\"\n🔍 **搜索** — 例如：\"搜索关于 Rust 的资料\"\n\n试试问我一个问题吧！".to_string()
            } else if lower.contains("bye") || lower.contains("再见") {
                "再见！很高兴和你聊天。如果以后需要帮助，随时回来找我！ 👋".to_string()
            } else {
                format!("收到你的消息：\"{}\"\n\n我是一个演示用的 AI 助手。试试问我关于天气、计算、时间或翻译的问题，我会调用相应的工具来回答你！", last_user_msg)
            };

            LlmResponse {
                content: Some(reply),
                tool_calls: None,
                finish_reason: "stop".to_string(),
                usage: Some(UsageInfo {
                    prompt_tokens: 30,
                    completion_tokens: 50,
                    total_tokens: 80,
                }),
            }
        }
    }

    /// Generate a mock streaming response.
    fn mock_stream(
        &self,
        messages: &[ChatMessage],
    ) -> Pin<Box<dyn Stream<Item = StreamChunk> + Send>> {
        let response = self.mock_response(messages, &ToolRegistry::new());
        let text = response.content.unwrap_or_else(|| "这是一个模拟的流式响应。".to_string());

        // Split text into character-level chunks for streaming effect
        let chars: Vec<char> = text.chars().collect();
        let chunks: Vec<StreamChunk> = chars
            .iter()
            .enumerate()
            .map(|(i, c)| StreamChunk {
                delta_content: Some(c.to_string()),
                delta_tool_calls: None,
                finish_reason: if i == chars.len() - 1 { Some("stop".to_string()) } else { None },
            })
            .collect();

        let stream = tokio_stream::iter(chunks);
        Box::pin(stream)
    }
}

/// Simple heuristic to extract city name from user message.
fn extract_city_name(msg: &str) -> String {
    let known_cities = [
        "北京", "上海", "广州", "深圳", "杭州", "成都", "重庆", "武汉", "南京", "西安",
        "Tokyo", "London", "Paris", "New York", "San Francisco", "Berlin", "Sydney",
    ];

    for city in &known_cities {
        if msg.contains(city) {
            return city.to_string();
        }
    }

    // Fallback: try to find a word after "weather" or "天气"
    let lower = msg.to_lowercase();
    if let Some(pos) = lower.find("weather") {
        let after = &msg[pos + 7..].trim();
        if let Some(word) = after.split_whitespace().next() {
            let cleaned = word.trim_matches(|c: char| !c.is_alphabetic());
            if !cleaned.is_empty() {
                return cleaned.to_string();
            }
        }
    }

    "Beijing".to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_city_name() {
        assert_eq!(extract_city_name("北京天气怎么样"), "北京");
        assert_eq!(extract_city_name("What's the weather in Tokyo?"), "Tokyo");
        assert_eq!(extract_city_name("random message"), "Beijing");
    }

    #[test]
    fn test_mock_response_greeting() {
        let config = Config::from_env();
        let client = LlmClient::new(config);
        let messages = vec![ChatMessage {
            role: "user".to_string(),
            content: Some("你好".to_string()),
            tool_calls: None,
            tool_call_id: None,
            name: None,
        }];
        let registry = ToolRegistry::new();
        let resp = client.mock_response(&messages, &registry);
        assert!(resp.content.is_some());
        assert!(resp.tool_calls.is_none());
    }

    #[test]
    fn test_mock_response_weather() {
        let config = Config::from_env();
        let client = LlmClient::new(config);
        let messages = vec![ChatMessage {
            role: "user".to_string(),
            content: Some("北京天气怎么样".to_string()),
            tool_calls: None,
            tool_call_id: None,
            name: None,
        }];
        let registry = ToolRegistry::new();
        let resp = client.mock_response(&messages, &registry);
        assert!(resp.content.is_none());
        assert!(resp.tool_calls.is_some());
        let calls = resp.tool_calls.unwrap();
        assert_eq!(calls[0].function.name, "get_weather");
    }
}
