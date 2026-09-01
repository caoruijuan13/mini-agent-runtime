use std::env;

/// Server configuration loaded from environment variables.
#[derive(Debug, Clone)]
pub struct Config {
    /// Host to bind the server to (default: 127.0.0.1)
    pub host: String,
    /// Port to listen on (default: 3000)
    pub port: u16,
    /// LLM provider: "openai" or "mock" (default: mock)
    pub llm_provider: String,
    /// OpenAI API key (required when provider is "openai")
    pub openai_api_key: String,
    /// OpenAI base URL (default: https://api.openai.com/v1)
    pub openai_base_url: String,
    /// Model name (default: gpt-4o-mini)
    pub model: String,
    /// Max tokens for LLM response (default: 2048)
    pub max_tokens: u32,
    /// Temperature for LLM (default: 0.7)
    pub temperature: f64,
}

impl Default for Config {
    /// Pure defaults with no `.env` or process-environment side effects.
    ///
    /// This is also the canonical deterministic configuration for tests.
    fn default() -> Self {
        Self {
            host: "127.0.0.1".to_string(),
            port: 3000,
            llm_provider: "mock".to_string(),
            openai_api_key: String::new(),
            openai_base_url: "https://api.openai.com/v1".to_string(),
            model: "gpt-4o-mini".to_string(),
            max_tokens: 2048,
            temperature: 0.7,
        }
    }
}

impl Config {
    /// Load configuration from environment variables with sensible defaults.
    pub fn from_env() -> Self {
        // Try to load .env file (ignore if not found)
        let _ = dotenvy::dotenv();

        let defaults = Self::default();

        Self {
            host: env::var("HOST").unwrap_or(defaults.host),
            port: env::var("PORT")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(defaults.port),
            llm_provider: env::var("LLM_PROVIDER").unwrap_or(defaults.llm_provider),
            openai_api_key: env::var("OPENAI_API_KEY").unwrap_or(defaults.openai_api_key),
            openai_base_url: env::var("OPENAI_BASE_URL").unwrap_or(defaults.openai_base_url),
            model: env::var("MODEL").unwrap_or(defaults.model),
            max_tokens: env::var("MAX_TOKENS")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(defaults.max_tokens),
            temperature: env::var("TEMPERATURE")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(defaults.temperature),
        }
    }

    /// Check if we're running in mock mode (no real LLM).
    pub fn is_mock(&self) -> bool {
        self.llm_provider == "mock"
    }

    /// Validate configuration at startup.
    pub fn validate(&self) -> Result<(), String> {
        if self.llm_provider == "openai" && self.openai_api_key.is_empty() {
            return Err("OPENAI_API_KEY is required when LLM_PROVIDER=openai".to_string());
        }
        if self.max_tokens == 0 || self.max_tokens > 128_000 {
            return Err("MAX_TOKENS must be between 1 and 128000".to_string());
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_config() {
        let config = Config::default();
        assert_eq!(config.host, "127.0.0.1");
        assert_eq!(config.port, 3000);
        assert!(config.is_mock());
    }

    #[test]
    fn test_validate_mock_ok() {
        let config = Config::default();
        assert!(config.validate().is_ok());
    }
}
