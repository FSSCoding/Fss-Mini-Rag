# LLM Provider Setup Guide

This guide shows how to configure FSS-Mini-RAG with different LLM providers for synthesis and query expansion features.

## Quick Provider Comparison

| Provider | Cost | Setup Difficulty | Quality | Privacy | Internet Required |
|----------|------|------------------|---------|---------|-------------------|
| **LM Studio** | Free | Easy | Good | Excellent | No |
| **vLLM** | Free | Medium | Good | Excellent | No |
| **OpenRouter** | Low ($0.10-0.50/M) | Medium | Excellent | Fair | Yes |
| **OpenAI** | Medium ($0.15-2.50/M) | Medium | Excellent | Fair | Yes |
| **Anthropic** | Medium-High | Medium | Excellent | Fair | Yes |

## Local Providers (Recommended)

### LM Studio (Recommended for Beginners)

**Best for:** GUI users, model experimentation, privacy

```yaml
llm:
  provider: openai
  api_base: http://localhost:1234/v1
  api_key: "not-needed"
  synthesis_model: "any"
  expansion_model: "any"
  enable_synthesis: false
  synthesis_temperature: 0.3
```

**Setup:**
1. Download [LM Studio](https://lmstudio.ai)
2. Install any model from the catalog
3. Start local server (default port 1234)
4. Use config above

### vLLM

**Best for:** Performance, multi-GPU, serving multiple models

```yaml
llm:
  provider: openai
  api_base: http://localhost:8080/v1
  api_key: "not-needed"
  synthesis_model: "auto"
  enable_synthesis: false
  synthesis_temperature: 0.3
```

**Setup:**
1. Install vLLM: `pip install vllm`
2. Start server: `vllm serve <model-name>`
3. Configure the endpoint URL in config

## Cloud Providers

### OpenRouter (Best Value)

**Best for:** Access to many models, reasonable pricing

```yaml
llm:
  provider: openai
  api_base: https://openrouter.ai/api/v1
  api_key: "your-api-key-here"
  synthesis_model: "meta-llama/llama-3.1-8b-instruct:free"
  expansion_model: "meta-llama/llama-3.1-8b-instruct:free"
  enable_synthesis: false
  synthesis_temperature: 0.3
  timeout: 30
```

**Setup:**
1. Sign up at [openrouter.ai](https://openrouter.ai)
2. Create API key in dashboard
3. Add $5-10 credits (goes far with efficient models)
4. Replace `your-api-key-here` with actual key

**Budget models:**
- `meta-llama/llama-3.1-8b-instruct:free` — Free tier
- `openai/gpt-4o-mini` — $0.15 per million tokens
- `anthropic/claude-3-haiku` — $0.25 per million tokens

### OpenAI (Premium Quality)

**Best for:** Reliability, advanced features

```yaml
llm:
  provider: openai
  api_key: "your-openai-api-key"
  synthesis_model: "gpt-4o-mini"
  expansion_model: "gpt-4o-mini"
  enable_synthesis: false
  synthesis_temperature: 0.3
  timeout: 30
```

**Setup:**
1. Sign up at [platform.openai.com](https://platform.openai.com)
2. Add payment method
3. Create API key
4. Start with `gpt-4o-mini` for cost efficiency

### Anthropic Claude (Code Expert)

**Best for:** Code analysis, thoughtful responses

```yaml
llm:
  provider: anthropic
  api_key: "your-anthropic-api-key"
  synthesis_model: "claude-3-haiku-20240307"
  expansion_model: "claude-3-haiku-20240307"
  enable_synthesis: false
  synthesis_temperature: 0.3
  timeout: 30
```

## Testing Your Setup

### 1. Basic Functionality Test
```bash
# Test without LLM (should always work)
rag-mini search "authentication"
```

### 2. Synthesis Test
```bash
# Test LLM integration
rag-mini search "authentication" --synthesize
```

### 3. GUI Test
```bash
# Launch GUI and use Preferences > Test Connection
rag-mini gui
```

### 4. Query Expansion Test
Enable `expand_queries: true` in config, then:
```bash
rag-mini search "auth"
# Should automatically expand to "auth authentication login user session"
```

## Configuration Tips

### For Budget-Conscious Users
```yaml
llm:
  synthesis_model: "gpt-4o-mini"
  enable_synthesis: false         # Manual control via --synthesize
  synthesis_temperature: 0.1     # Factual responses
  max_expansion_terms: 4          # Shorter expansions
```

### For Quality-Focused Users
```yaml
llm:
  synthesis_model: "gpt-4o"
  enable_synthesis: true
  synthesis_temperature: 0.3
  enable_thinking: true
  max_expansion_terms: 8
```

### For Privacy-Focused Users
```yaml
# Use only local providers
embedding:
  provider: openai
  base_url: http://localhost:1234/v1
llm:
  provider: openai
  api_base: http://localhost:1234/v1
```

## Troubleshooting

### Connection Issues
- **Local:** Ensure LM Studio or vLLM is running
- **Cloud:** Check API key and internet connection

### Model Not Found
- **Local:** Load a model in LM Studio or start vLLM with a model
- **Cloud:** Check provider's model list documentation

### High Costs
- Use mini/haiku models instead of full versions
- Set `enable_synthesis: false` and use `--synthesize` selectively
- Reduce `max_expansion_terms` to 4-6

### Slow Responses
- **Local:** Try smaller models
- **Cloud:** Increase `timeout` or switch providers

## Environment Variables (Alternative Setup)

Instead of putting API keys in config files, use environment variables:

```bash
# In your shell profile (.bashrc, .zshrc, etc.)
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key"
export OPENROUTER_API_KEY="your-openrouter-key"
```

## Further Reading

- [OpenRouter Pricing](https://openrouter.ai/docs#models)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Anthropic Claude Documentation](https://docs.anthropic.com/claude)
- [LM Studio Getting Started](https://lmstudio.ai/docs)
