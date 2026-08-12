mod config;
mod llm;
mod server;
mod tools;

use config::Config;
use llm::LlmClient;
use server::AppState;
use std::net::SocketAddr;
use std::sync::Arc;
use tracing::info;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

#[tokio::main]
async fn main() {
    // Initialize tracing (respects RUST_LOG env var)
    tracing_subscriber::registry()
        .with(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "mini_agent_server=info,tower_http=info".into()),
        )
        .with(tracing_subscriber::fmt::layer())
        .init();

    // Load configuration
    let config = Config::from_env();

    // Validate configuration
    if let Err(e) = config.validate() {
        eprintln!("Configuration error: {e}");
        std::process::exit(1);
    }

    // Create shared state
    let state = Arc::new(AppState {
        llm: LlmClient::new(config.clone()),
        config: config.clone(),
        tools: tools::default_tool_registry(),
    });

    // Build router
    let app = server::build_router(state);

    // Bind address
    let addr = SocketAddr::from((
        config.host.parse::<std::net::IpAddr>().unwrap_or_else(|_| {
            eprintln!("Invalid HOST: {}", config.host);
            std::process::exit(1);
        }),
        config.port,
    ));

    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();

    info!("═══════════════════════════════════════════════");
    info!("  mini-agent-runtime server v{}", env!("CARGO_PKG_VERSION"));
    info!("═══════════════════════════════════════════════");
    info!("  Listening on: http://{}", addr);
    info!("  LLM provider: {}", config.llm_provider);
    info!("  Model:        {}", config.model);
    info!("  Tools:        {} available", tools::default_tool_registry().definitions().len());
    info!("═══════════════════════════════════════════════");
    info!("  Endpoints:");
    info!("    GET  /health  — Health check");
    info!("    POST /chat    — Chat completion (JSON or SSE)");
    info!("    GET  /tools   — List available tools");
    info!("═══════════════════════════════════════════════");

    axum::serve(listener, app)
        .await
        .expect("Server failed to start");
}
