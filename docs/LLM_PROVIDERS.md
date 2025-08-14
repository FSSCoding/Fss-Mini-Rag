# 🤖 LLM Provider Setup Guide

This guide shows how to configure FSS-Mini-RAG with different LLM providers for synthesis and query expansion features.

## 🎯 Quick Provider Comparison

| Provider | Cost | Setup Difficulty | Quality | Privacy | Internet Required |
|----------|------|------------------|---------|---------|-------------------|
| **Ollama** | Free | Easy | Good | Excellent | No |
| **LM Studio** | Free | Easy | Good | Excellent | No |
| **OpenRouter** | Low ($0.10-0.50/M) | Medium | Excellent | Fair | Yes |
| **OpenAI** | Medium ($0.15-2.50/M) | Medium | Excellent | Fair | Yes |
| **Anthropic** | Medium-High | Medium | Excellent | Fair | Yes |

## 🏠 Local Providers (Recommended for Beginners)

### Ollama (Default)

**Best for:** Privacy, learning, no ongoing costs

```yaml
llm:
  provider: ollama
  ollama_host: localhost:11434
  synthesis_model: llama3.2
  expansion_model: llama3.2
  enable_synthesis: false
  synthesis_temperature: 0.3
  cpu_optimized: true
  enable_thinking: true
```

**Setup:**
1. Install Ollama: `curl -fsSL https://ollama.ai/install.sh | sh`
2. Start service: `ollama serve`
3. Download model: `ollama pull llama3.2`
4. Test: `./rag-mini search /path/to/project "test" --synthesize`

**Recommended Models:**
- `qwen3:0.6b` - Ultra-fast, good for CPU-only systems
- `llama3.2` - Balanced quality and speed  
- `llama3.1:8b` - Higher quality, needs more RAM

### LM Studio

**Best for:** GUI users, model experimentation

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

## ☁️ Cloud Providers (For Advanced Users)

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

**Budget Models:**
- `meta-llama/llama-3.1-8b-instruct:free` - Free tier
- `openai/gpt-4o-mini` - $0.15 per million tokens
- `anthropic/claude-3-haiku` - $0.25 per million tokens

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

**Setup:**
1. Sign up at [console.anthropic.com](https://console.anthropic.com)
2. Add credits to account
3. Create API key
4. Start with Claude Haiku for budget-friendly option

## 🧪 Testing Your Setup

### 1. Basic Functionality Test
```bash
# Test without LLM (should always work)
./rag-mini search /path/to/project "authentication"
```

### 2. Synthesis Test
```bash
# Test LLM integration
./rag-mini search /path/to/project "authentication" --synthesize
```

### 3. Interactive Test
```bash
# Test exploration mode
./rag-mini explore /path/to/project
# Then ask: "How does authentication work in this codebase?"
```

### 4. Query Expansion Test
Enable `expand_queries: true` in config, then:
```bash
./rag-mini search /path/to/project "auth"
# Should automatically expand to "auth authentication login user session"
```

## 🛠️ Configuration Tips

### For Budget-Conscious Users
```yaml
llm:
  synthesis_model: "gpt-4o-mini"  # or claude-haiku
  enable_synthesis: false         # Manual control
  synthesis_temperature: 0.1     # Factual responses
  max_expansion_terms: 4          # Shorter expansions
```

### For Quality-Focused Users
```yaml
llm:
  synthesis_model: "gpt-4o"       # or claude-sonnet
  enable_synthesis: true          # Always on
  synthesis_temperature: 0.3     # Balanced creativity
  enable_thinking: true           # Show reasoning
  max_expansion_terms: 8          # Comprehensive expansion
```

### For Privacy-Focused Users
```yaml
# Use only local providers
embedding:
  preferred_method: ollama        # Local embeddings
llm:
  provider: ollama               # Local LLM
  # Never use cloud providers
```

## 🔧 Troubleshooting

### Connection Issues
- **Local:** Ensure Ollama/LM Studio is running: `ps aux | grep ollama`
- **Cloud:** Check API key and internet: `curl -H "Authorization: Bearer $API_KEY" https://api.openai.com/v1/models`

### Model Not Found
- **Ollama:** `ollama pull model-name`
- **Cloud:** Check provider's model list documentation

### High Costs
- Use mini/haiku models instead of full versions
- Set `enable_synthesis: false` and use `--synthesize` selectively
- Reduce `max_expansion_terms` to 4-6

### Poor Quality
- Try higher-tier models (gpt-4o, claude-sonnet)
- Adjust `synthesis_temperature` (0.1 = factual, 0.5 = creative)
- Enable `expand_queries` for better search coverage

### Slow Responses
- **Local:** Try smaller models (qwen3:0.6b)
- **Cloud:** Increase `timeout` or switch providers
- **General:** Reduce `max_size` in chunking config

## 📋 Environment Variables (Alternative Setup)

Instead of putting API keys in config files, use environment variables:

```bash
# In your shell profile (.bashrc, .zshrc, etc.)
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key"
export OPENROUTER_API_KEY="your-openrouter-key"
```

Then in config:
```yaml
llm:
  api_key: "${OPENAI_API_KEY}"  # Reads from environment
```

## 🚀 Advanced: Multi-Provider Setup

You can create different configs for different use cases:

```bash
# Fast local analysis
cp examples/config-beginner.yaml .mini-rag/config-local.yaml

# High-quality cloud analysis  
cp examples/config-llm-providers.yaml .mini-rag/config-cloud.yaml
# Edit to use OpenAI/Claude

# Switch configs as needed
ln -sf config-local.yaml .mini-rag/config.yaml   # Use local
ln -sf config-cloud.yaml .mini-rag/config.yaml   # Use cloud
```

## 📚 Further Reading

- [Ollama Model Library](https://ollama.ai/library)
- [OpenRouter Pricing](https://openrouter.ai/docs#models)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Anthropic Claude Documentation](https://docs.anthropic.com/claude)
- [LM Studio Getting Started](https://lmstudio.ai/docs)

---

💡 **Pro Tip:** Start with local Ollama for learning, then upgrade to cloud providers when you need production-quality analysis or are working with large codebases.