use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Tool parameter property definition (JSON Schema subset).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolProperty {
    pub r#type: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub enum_values: Option<Vec<String>>,
}

/// Tool parameter schema.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolParameters {
    pub r#type: String,
    pub properties: HashMap<String, ToolProperty>,
    pub required: Vec<String>,
}

/// A tool definition that can be sent to LLM APIs.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolDefinition {
    pub name: String,
    pub description: String,
    pub parameters: ToolParameters,
}

/// A tool call request from the LLM.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolCall {
    pub id: String,
    pub name: String,
    pub arguments: serde_json::Value,
}

/// Tool result returned after execution.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolResult {
    pub tool_call_id: String,
    pub name: String,
    pub content: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub is_error: Option<bool>,
}

/// Registry that holds all available tool definitions.
#[derive(Debug, Clone)]
pub struct ToolRegistry {
    tools: Vec<ToolDefinition>,
}

impl ToolRegistry {
    pub fn new() -> Self {
        Self { tools: Vec::new() }
    }

    /// Register a new tool definition.
    pub fn register(&mut self, tool: ToolDefinition) {
        self.tools.push(tool);
    }

    /// Get all tool definitions (for sending to LLM).
    pub fn definitions(&self) -> &[ToolDefinition] {
        &self.tools
    }

    /// Convert to OpenAI-compatible tool format.
    pub fn to_openai_tools(&self) -> Vec<serde_json::Value> {
        self.tools
            .iter()
            .map(|t| {
                serde_json::json!({
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters,
                    }
                })
            })
            .collect()
    }

    /// Find a tool by name.
    pub fn get(&self, name: &str) -> Option<&ToolDefinition> {
        self.tools.iter().find(|t| t.name == name)
    }
}

impl Default for ToolRegistry {
    fn default() -> Self {
        Self::new()
    }
}

/// Create the default set of server-side tool definitions.
/// These describe the tools the Python agent can execute.
pub fn default_tool_registry() -> ToolRegistry {
    let mut registry = ToolRegistry::new();

    // --- get_weather ---
    registry.register(ToolDefinition {
        name: "get_weather".to_string(),
        description: "Get the current weather for a given city. Returns temperature, condition, and humidity.".to_string(),
        parameters: ToolParameters {
            r#type: "object".to_string(),
            properties: {
                let mut props = HashMap::new();
                props.insert("city".to_string(), ToolProperty {
                    r#type: "string".to_string(),
                    description: Some("The city name, e.g. 'Beijing' or 'New York'".to_string()),
                    enum_values: None,
                });
                props.insert("unit".to_string(), ToolProperty {
                    r#type: "string".to_string(),
                    description: Some("Temperature unit: 'celsius' or 'fahrenheit'".to_string()),
                    enum_values: Some(vec!["celsius".to_string(), "fahrenheit".to_string()]),
                });
                props
            },
            required: vec!["city".to_string()],
        },
    });

    // --- calculate ---
    registry.register(ToolDefinition {
        name: "calculate".to_string(),
        description: "Evaluate a mathematical expression. Supports +, -, *, /, **, sqrt, sin, cos, tan, log, pi, e.".to_string(),
        parameters: ToolParameters {
            r#type: "object".to_string(),
            properties: {
                let mut props = HashMap::new();
                props.insert("expression".to_string(), ToolProperty {
                    r#type: "string".to_string(),
                    description: Some("The mathematical expression to evaluate, e.g. '2 ** 10' or 'sqrt(144)'".to_string()),
                    enum_values: None,
                });
                props
            },
            required: vec!["expression".to_string()],
        },
    });

    // --- get_current_time ---
    registry.register(ToolDefinition {
        name: "get_current_time".to_string(),
        description: "Get the current date and time in a specified timezone.".to_string(),
        parameters: ToolParameters {
            r#type: "object".to_string(),
            properties: {
                let mut props = HashMap::new();
                props.insert("timezone".to_string(), ToolProperty {
                    r#type: "string".to_string(),
                    description: Some("IANA timezone name, e.g. 'Asia/Shanghai', 'America/New_York', 'UTC'".to_string()),
                    enum_values: None,
                });
                props
            },
            required: vec!["timezone".to_string()],
        },
    });

    // --- translate ---
    registry.register(ToolDefinition {
        name: "translate".to_string(),
        description: "Translate text from one language to another.".to_string(),
        parameters: ToolParameters {
            r#type: "object".to_string(),
            properties: {
                let mut props = HashMap::new();
                props.insert("text".to_string(), ToolProperty {
                    r#type: "string".to_string(),
                    description: Some("The text to translate".to_string()),
                    enum_values: None,
                });
                props.insert("target_language".to_string(), ToolProperty {
                    r#type: "string".to_string(),
                    description: Some("Target language name, e.g. 'English', 'Chinese', 'Japanese'".to_string()),
                    enum_values: None,
                });
                props.insert("source_language".to_string(), ToolProperty {
                    r#type: "string".to_string(),
                    description: Some("Source language name (default: auto-detect)".to_string()),
                    enum_values: None,
                });
                props
            },
            required: vec!["text".to_string(), "target_language".to_string()],
        },
    });

    // --- search_knowledge ---
    registry.register(ToolDefinition {
        name: "search_knowledge".to_string(),
        description: "Search a local knowledge base for relevant information. Returns matching snippets.".to_string(),
        parameters: ToolParameters {
            r#type: "object".to_string(),
            properties: {
                let mut props = HashMap::new();
                props.insert("query".to_string(), ToolProperty {
                    r#type: "string".to_string(),
                    description: Some("The search query".to_string()),
                    enum_values: None,
                });
                props.insert("max_results".to_string(), ToolProperty {
                    r#type: "number".to_string(),
                    description: Some("Maximum number of results to return (default: 3)".to_string()),
                    enum_values: None,
                });
                props
            },
            required: vec!["query".to_string()],
        },
    });

    registry
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_registry_register_and_get() {
        let mut registry = ToolRegistry::new();
        let tool = ToolDefinition {
            name: "test_tool".to_string(),
            description: "A test tool".to_string(),
            parameters: ToolParameters {
                r#type: "object".to_string(),
                properties: HashMap::new(),
                required: vec![],
            },
        };
        registry.register(tool);
        assert_eq!(registry.definitions().len(), 1);
        assert!(registry.get("test_tool").is_some());
        assert!(registry.get("nonexistent").is_none());
    }

    #[test]
    fn test_default_registry() {
        let registry = default_tool_registry();
        assert!(registry.definitions().len() >= 5);
        assert!(registry.get("get_weather").is_some());
        assert!(registry.get("calculate").is_some());
        assert!(registry.get("get_current_time").is_some());
        assert!(registry.get("translate").is_some());
        assert!(registry.get("search_knowledge").is_some());
    }

    #[test]
    fn test_to_openai_tools() {
        let registry = default_tool_registry();
        let openai_tools = registry.to_openai_tools();
        assert!(!openai_tools.is_empty());
        // Verify structure
        let first = &openai_tools[0];
        assert_eq!(first["type"], "function");
        assert!(first["function"]["name"].is_string());
    }
}
