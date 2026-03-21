# 📚 Beginner's Glossary - RAG Terms Made Simple

*Confused by all the technical terms? Don't worry! This guide explains everything in plain English.*

---

## 🤖 **RAG** - Retrieval Augmented Generation
**What it is:** A fancy way of saying "search your code and get AI explanations"

**Simple explanation:** Instead of just searching for keywords (like Google), RAG finds code that's *similar in meaning* to what you're looking for, then has an AI explain it to you.

**Real example:** 
- You search for "user authentication"  
- RAG finds code about login systems, password validation, and user sessions
- AI explains: "This code handles user logins using email/password, stores sessions in cookies, and validates users on each request"

---

## 🧩 **Chunks** - Bite-sized pieces of your code
**What it is:** Your code files broken into smaller, searchable pieces

**Simple explanation:** RAG can't search entire huge files efficiently, so it breaks them into "chunks" - like cutting a pizza into slices. Each chunk is usually one function, one class, or a few related lines.

**Why it matters:**
- Too small chunks = missing context ("this variable" but what variable?)
- Too big chunks = too much unrelated stuff in search results
- Just right = perfect context for understanding what code does

**Real example:**
```python
# This would be one chunk:
def login_user(email, password):
    """Authenticate user with email and password."""
    user = find_user_by_email(email)
    if user and check_password(user, password):
        create_session(user)
        return True
    return False
```

---

## 🧠 **Embeddings** - Code "fingerprints" 
**What it is:** A way to convert your code into numbers that computers can compare

**Simple explanation:** Think of embeddings like DNA fingerprints for your code. Similar code gets similar fingerprints. The computer can then find code with similar "fingerprints" to what you're searching for.

**The magic:** Code that does similar things gets similar embeddings, even if the exact words are different:
- `login_user()` and `authenticate()` would have similar embeddings
- `calculate_tax()` and `login_user()` would have very different embeddings

**You don't need to understand the technical details** - just know that embeddings help find semantically similar code, not just exact word matches.

---

## 🔍 **Vector Search** vs **Keyword Search**
**Keyword search (like Google):** Finds exact word matches
- Search "login" → finds code with the word "login"
- Misses: authentication, signin, user_auth

**Vector search (the RAG way):** Finds similar *meaning*
- Search "login" → finds login, authentication, signin, user validation
- Uses those embedding "fingerprints" to find similar concepts

**FSS-Mini-RAG uses both** for the best results!

---

## 📊 **Similarity Score** - How relevant is this result?
**What it is:** A number from 0.0 to 1.0 showing how closely your search matches the result

**Simple explanation:** 
- 1.0 = Perfect match (very rare)
- 0.8+ = Excellent match  
- 0.5+ = Good match
- 0.3+ = Somewhat relevant
- 0.1+ = Might be useful
- Below 0.1 = Probably not what you want

**In practice:** Most useful results are between 0.2-0.8

---

## 🎯 **BM25** - The keyword search boost
**What it is:** A fancy algorithm that finds exact word matches (like Google search)

**Simple explanation:** While embeddings find *similar meaning*, BM25 finds *exact words*. Using both together gives you the best of both worlds.

**Example:**
- You search for "password validation"
- Embeddings find: authentication functions, login methods, user security
- BM25 finds: code with the exact words "password" and "validation"
- Combined = comprehensive results

**Keep it enabled** unless you're getting too many irrelevant results.

---

## 🔄 **Query Expansion** - Making your search smarter
**What it is:** Automatically adding related terms to your search

**Simple explanation:** When you search for "auth", the system automatically expands it to "auth authentication login signin user validate".

**Pros:** Much better, more comprehensive results  
**Cons:** Slower search, sometimes too broad

**When to use:**
- Turn ON for: Complex searches, learning new codebases
- Turn OFF for: Quick lookups, very specific searches

---

## 🤖 **LLM** - Large Language Model (The AI Brain)
**What it is:** The AI that reads your search results and explains them in plain English

**Simple explanation:** After finding relevant code chunks, the LLM reads them like a human would and gives you a summary like: "This code handles user registration by validating email format, checking for existing users, hashing passwords, and saving to database."

**Models you might see:**
- **qwen3:0.6b** - Ultra-fast, good for most questions
- **qwen3:4b** - Slower but more detailed
- **auto** - Picks the best available model

---

## 🧮 **Synthesis** vs **Exploration** - Two ways to get answers

### 🚀 **Synthesis Mode** (Fast & Consistent)
**What it does:** Quick, factual answers about your code
**Best for:** "What does this function do?" "Where is authentication handled?" "How does the database connection work?"
**Speed:** Very fast (no "thinking" overhead)

### 🧠 **Exploration Mode** (Deep & Interactive)
**What it does:** Detailed analysis with reasoning, remembers conversation
**Best for:** "Why is this function slow?" "What are the security issues here?" "How would I add a new feature?"
**Features:** Shows its reasoning process, you can ask follow-up questions

---

## ⚡ **Streaming** - Handling huge files without crashing
**What it is:** Processing large files in smaller batches instead of all at once

**Simple explanation:** Imagine trying to eat an entire cake at once vs. eating it slice by slice. Streaming is like eating slice by slice - your computer won't choke on huge files.

**When it kicks in:** Files larger than 1MB (that's about 25,000 lines of code)

---

## 🏷️ **Semantic** vs **Fixed** Chunking
**Semantic chunking (RECOMMENDED):** Smart splitting that respects code structure
- Keeps functions together
- Keeps classes together  
- Respects natural code boundaries

**Fixed chunking:** Simple splitting that just cuts at size limits
- Faster processing
- Might cut functions in half
- Less intelligent but more predictable

**For beginners:** Always use semantic chunking unless you have a specific reason not to.

---

## ❓ **Common Questions**

**Q: Do I need to understand embeddings to use this?**  
A: Nope! Just know they help find similar code. The system handles all the technical details.

**Q: What's a good similarity threshold for beginners?**  
A: Start with 0.1. If you get too many results, try 0.2. If you get too few, try 0.05.

**Q: Should I enable query expansion?**  
A: For learning new codebases: YES. For quick specific searches: NO. The TUI enables it automatically when helpful.

**Q: Which embedding method should I choose?**  
A: Use "auto" - it tries the best option and falls back gracefully if needed.

**Q: What if I don't have Ollama installed?**  
A: No problem! The system will automatically fall back to other methods that work without any additional software.

---

## 🚀 **Quick Start Recommendations**

**For absolute beginners:**
1. Keep all default settings
2. Use the TUI interface to start
3. Try simple searches like "user login" or "database connection"
4. Gradually try the CLI commands as you get comfortable

**For faster results:**
- Set `similarity_threshold: 0.2`
- Set `expand_queries: false`
- Use synthesis mode instead of exploration

**For learning new codebases:**
- Set `expand_queries: true`
- Use exploration mode
- Ask "why" and "how" questions

---

**Remember:** This is a learning tool! Don't be afraid to experiment with settings and see what works best for your projects. The beauty of FSS-Mini-RAG is that it's designed to be beginner-friendly while still being powerful.