use crate::config::Config;
use crate::llm::{ChatMessage, LlmClient, LlmResponse, StreamChunk};
use crate::tools::ToolRegistry;
use axum::{
    extract::State,
    http::StatusCode,
    response::{
        sse::{Event, Sse},
        IntoResponse, Json,
    },
    routing::{get, post},
    Router,
};
use serde::{Deserialize, Serialize};
use std::convert::Infallible;
use std::sync::Arc;
use tokio_stream::StreamExt as _;
use tower_http::cors::{Any, CorsLayer};
use tower_http::trace::TraceLayer;
use tracing::info;

/// Shared application state.
pub struct AppState {
    pub config: Config,
    pub llm: LlmClient,
    pub tools: ToolRegistry,
}

/// Request body for the /chat endpoint.
#[derive(Debug, Deserialize)]
pub struct ChatRequest {
    pub messages: Vec<ChatMessage>,
    #[serde(default)]
    pub stream: bool,
}

/// Non-streaming chat response.
#[derive(Debug, Serialize)]
pub struct ChatResponse {
    pub content: Option<String>,
    pub tool_calls: Option<Vec<serde_json::Value>>,
    pub finish_reason: String,
    pub usage: Option<serde_json::Value>,
}

impl From<LlmResponse> for ChatResponse {
    fn from(r: LlmResponse) -> Self {
        Self {
            content: r.content,
            tool_calls: r.tool_calls.map(|calls| {
                calls
                    .into_iter()
                    .map(|c| {
                        serde_json::json!({
                            "id": c.id,
                            "type": c.r#type,
                            "function": {
                                "name": c.function.name,
                                "arguments": c.function.arguments,
                            }
                        })
                    })
                    .collect()
            }),
            finish_reason: r.finish_reason,
            usage: r.usage.map(|u| {
                serde_json::json!({
                    "prompt_tokens": u.prompt_tokens,
                    "completion_tokens": u.completion_tokens,
                    "total_tokens": u.total_tokens,
                })
            }),
        }
    }
}

/// Health check response.
#[derive(Debug, Serialize)]
pub struct HealthResponse {
    pub status: String,
    pub version: String,
    pub llm_provider: String,
    pub tools_count: usize,
}

/// Tool info for /tools endpoint.
#[derive(Debug, Serialize)]
pub struct ToolInfo {
    pub name: String,
    pub description: String,
}

/// Build the Axum router with all routes and middleware.
pub fn build_router(state: Arc<AppState>) -> Router {
    let cors = CorsLayer::new()
        .allow_origin(Any)
        .allow_methods(Any)
        .allow_headers(Any);

    Router::new()
        .route("/health", get(health_handler))
        .route("/chat", post(chat_handler))
        .route("/tools", get(tools_handler))
        .layer(cors)
        .layer(TraceLayer::new_for_http())
        .with_state(state)
}

/// GET /health — server health check.
async fn health_handler(State(state): State<Arc<AppState>>) -> Json<HealthResponse> {
    Json(HealthResponse {
        status: "ok".to_string(),
        version: env!("CARGO_PKG_VERSION").to_string(),
        llm_provider: state.config.llm_provider.clone(),
        tools_count: state.tools.definitions().len(),
    })
}

/// POST /chat — chat completion (supports streaming via SSE).
async fn chat_handler(
    State(state): State<Arc<AppState>>,
    Json(req): Json<ChatRequest>,
) -> impl IntoResponse {
    info!(
        msg_count = req.messages.len(),
        stream = req.stream,
        "Chat request received"
    );

    if req.stream {
        // Streaming response via SSE
        match state.llm.chat_stream(&req.messages, &state.tools).await {
            Ok(stream) => {
                let sse_stream = stream.map(|chunk: StreamChunk| {
                    let data = serde_json::json!({
                        "content": chunk.delta_content,
                        "finish_reason": chunk.finish_reason,
                    });
                    let event = Event::default().json_data(data).unwrap_or_else(|_| {
                        Event::default().data("{}")
                    });
                    Ok::<_, Infallible>(event)
                });
                Sse::new(sse_stream)
                    .keep_alive(
                        axum::response::sse::KeepAlive::new()
                            .interval(std::time::Duration::from_secs(15)),
                    )
                    .into_response()
            }
            Err(e) => {
                let error_body = serde_json::json!({"error": e});
                (StatusCode::INTERNAL_SERVER_ERROR, Json(error_body)).into_response()
            }
        }
    } else {
        // Non-streaming response
        match state.llm.chat(&req.messages, &state.tools).await {
            Ok(response) => {
                let chat_resp: ChatResponse = response.into();
                (StatusCode::OK, Json(chat_resp)).into_response()
            }
            Err(e) => {
                let error_body = serde_json::json!({"error": e});
                (StatusCode::INTERNAL_SERVER_ERROR, Json(error_body)).into_response()
            }
        }
    }
}

/// GET /tools — list available tool definitions.
async fn tools_handler(State(state): State<Arc<AppState>>) -> Json<Vec<ToolInfo>> {
    let tools = state
        .tools
        .definitions()
        .iter()
        .map(|t| ToolInfo {
            name: t.name.clone(),
            description: t.description.clone(),
        })
        .collect();
    Json(tools)
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::body::Body;
    use axum::http::Request;
    use tower::ServiceExt;

    fn test_state() -> Arc<AppState> {
        let config = Config::from_env();
        Arc::new(AppState {
            llm: LlmClient::new(config.clone()),
            config,
            tools: crate::tools::default_tool_registry(),
        })
    }

    #[tokio::test]
    async fn test_health_endpoint() {
        let app = build_router(test_state());
        let resp = app
            .oneshot(Request::builder().uri("/health").body(Body::empty()).unwrap())
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn test_tools_endpoint() {
        let app = build_router(test_state());
        let resp = app
            .oneshot(Request::builder().uri("/tools").body(Body::empty()).unwrap())
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn test_chat_endpoint() {
        let app = build_router(test_state());
        let body = serde_json::json!({
            "messages": [{"role": "user", "content": "你好"}],
            "stream": false
        });
        let resp = app
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/chat")
                    .header("Content-Type", "application/json")
                    .body(Body::from(serde_json::to_string(&body).unwrap()))
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::OK);
    }
}
