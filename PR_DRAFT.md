# Add Context Window Configuration for Optimal RAG Performance

## Problem Statement

Currently, FSS-Mini-RAG uses Ollama's default context window settings, which severely limits performance:

- **Default 2048 tokens** is inadequate for RAG applications
- Users can't configure context window for their hardware/use case
- No guidance on optimal context sizes for different models
- Inconsistent context handling across the codebase
- New users don't understand context window importance

## Impact on User Experience

**With 2048 token context window:**
- Only 1-2 responses possible before context truncation
- Thinking tokens consume significant context space
- Poor performance with larger document chunks
- Frustrated users who don't understand why responses degrade

**With proper context configuration:**
- 5-15+ responses in exploration mode
- Support for advanced use cases (15+ results, 4000+ character chunks)
- Better coding assistance and analysis
- Professional-grade RAG experience

## Proposed Solution

### 1. Enhanced Model Configuration Menu
Add context window selection alongside model selection with:
- **Development**: 8K tokens (fast, good for most cases)
- **Production**: 16K tokens (balanced performance)  
- **Advanced**: 32K+ tokens (heavy development work)

### 2. Educational Content
Help users understand:
- Why context window size matters for RAG
- Hardware implications of larger contexts
- Optimal settings for their use case
- Model-specific context capabilities

### 3. Consistent Implementation
- Update all Ollama API calls to use consistent context settings
- Ensure configuration applies across synthesis, expansion, and exploration
- Validate context sizes against model capabilities
- Provide clear error messages for invalid configurations

## Technical Implementation

Based on research findings:

### Model Context Capabilities
- **qwen3:0.6b/1.7b**: 32K token maximum
- **qwen3:4b**: 131K token maximum (YaRN extended)

### Recommended Context Sizes
```yaml
# Conservative (fast, low memory)
num_ctx: 8192    # ~6MB memory, excellent for exploration

# Balanced (recommended for most users)  
num_ctx: 16384   # ~12MB memory, handles complex analysis

# Advanced (heavy development work)
num_ctx: 32768   # ~24MB memory, supports large codebases
```

### Configuration Integration
- Add context window selection to TUI configuration menu
- Update config.yaml schema with context parameters
- Implement validation for model-specific limits
- Provide migration for existing configurations

## Benefits

1. **Improved User Experience**
   - Longer conversation sessions
   - Better analysis quality
   - Clear performance expectations

2. **Professional RAG Capability**
   - Support for enterprise-scale projects
   - Handles large codebases effectively
   - Enables advanced use cases

3. **Educational Value**
   - Users learn about context windows
   - Better understanding of RAG performance
   - Informed decision making

## Implementation Plan

1. **Phase 1**: Research Ollama context handling (✅ Complete)
2. **Phase 2**: Update configuration system
3. **Phase 3**: Enhance TUI with context selection
4. **Phase 4**: Update all API calls consistently
5. **Phase 5**: Add documentation and validation

## Questions for Review

1. Should we auto-detect optimal context based on available memory?
2. How should we handle model changes that affect context capabilities?
3. Should context be per-model or global configuration?
4. What validation should we provide for context/model combinations?

---

**This PR will significantly improve FSS-Mini-RAG's performance and user experience by properly configuring one of the most critical parameters for RAG systems.**