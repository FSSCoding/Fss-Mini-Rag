# Beginner's Glossary — RAG Terms Made Simple

*Confused by all the technical terms? This guide explains everything in plain English.*

---

## **RAG** — Retrieval Augmented Generation
**What it is:** A fancy way of saying "search your code and get AI explanations."

**Simple explanation:** Instead of just searching for keywords (like Google), RAG finds code that's *similar in meaning* to what you're looking for, then has an AI explain it to you.

**Real example:**
- You search for "user authentication"
- RAG finds code about login systems, password validation, and user sessions
- AI explains: "This code handles user logins using email/password, stores sessions in cookies, and validates users on each request"

---

## **Chunks** — Bite-sized pieces of your code
**What it is:** Your code files broken into smaller, searchable pieces.

**Simple explanation:** RAG can't search entire huge files efficiently, so it breaks them into "chunks" — like cutting a pizza into slices. Each chunk is usually one function, one class, or a few related lines.

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

## **Embeddings** — Code "fingerprints"
**What it is:** A way to convert your code into numbers that computers can compare.

**Simple explanation:** Think of embeddings like DNA fingerprints for your code. Similar code gets similar fingerprints. The computer can then find code with similar "fingerprints" to what you're searching for.

**The magic:** Code that does similar things gets similar embeddings, even if the exact words are different:
- `login_user()` and `authenticate()` would have similar embeddings
- `calculate_tax()` and `login_user()` would have very different embeddings

**You don't need to understand the technical details** — just know that embeddings help find semantically similar code, not just exact word matches.

---

## **Vector Search** vs **Keyword Search**
**Keyword search (like Google):** Finds exact word matches.
- Search "login" — finds code with the word "login"
- Misses: authentication, signin, user_auth

**Vector search (the RAG way):** Finds similar *meaning*.
- Search "login" — finds login, authentication, signin, user validation
- Uses those embedding "fingerprints" to find similar concepts

**FSS-Mini-RAG uses both** for the best results!

---

## **Similarity Score** — How relevant is this result?
**What it is:** A number showing how closely your search matches the result.

FSS-Mini-RAG uses RRF (Reciprocal Rank Fusion) scores which are small numbers. The display shows human-readable labels:

| Label | Meaning |
|-------|---------|
| HIGH | Excellent match |
| GOOD | Strong match |
| FAIR | Relevant |
| LOW | Somewhat relevant |
| WEAK | Might be useful |

---

## **BM25** — The keyword search boost
**What it is:** A fancy algorithm that finds exact word matches (like Google search).

**Simple explanation:** While embeddings find *similar meaning*, BM25 finds *exact words*. Using both together gives you the best of both worlds.

**Example:**
- You search for "password validation"
- Embeddings find: authentication functions, login methods, user security
- BM25 finds: code with the exact words "password" and "validation"
- Combined = comprehensive results

**Keep it enabled** unless you're getting too many irrelevant results.

---

## **Query Expansion** — Making your search smarter
**What it is:** Automatically adding related terms to your search.

**Simple explanation:** When you search for "auth", the system automatically expands it to "auth authentication login signin user validate".

**Pros:** Much better, more comprehensive results
**Cons:** Slower search, sometimes too broad

**When to use:**
- Turn ON for: Complex searches, learning new codebases
- Turn OFF for: Quick lookups, very specific searches

---

## **LLM** — Large Language Model (The AI Brain)
**What it is:** The AI that reads your search results and explains them in plain English.

**Simple explanation:** After finding relevant code chunks, the LLM reads them like a human would and gives you a summary like: "This code handles user registration by validating email format, checking for existing users, hashing passwords, and saving to database."

FSS-Mini-RAG works with any LLM via an OpenAI-compatible endpoint (LM Studio, vLLM, OpenAI, etc.).

---

## **Synthesis** — Getting AI explanations

**What it does:** After searching, the LLM reads the results and gives you a plain-English summary.

**How to use it:**
```bash
rag-mini search "authentication" --synthesize
```

**Speed:** Depends on your LLM server and model size. Small models (0.6B-1.7B) respond in 1-3 seconds.

---

## **Web Research** — Searching and scraping the web

**What it does:** Search the web for a topic, scrape the pages, extract clean content, and index it locally for searching.

**Three levels:**
1. **Scrape** — fetch specific URLs
2. **Search-web** — search the web and scrape results
3. **Research** — full pipeline with optional deep iterative cycles

---

## **Deep Research** — Autonomous research cycles

**What it does:** Given a topic and time budget, the system autonomously:
1. Searches the web
2. Scrapes results
3. Has an LLM analyse the corpus
4. Identifies gaps in knowledge
5. Generates new search queries
6. Repeats until time runs out
7. Produces a comprehensive research report

**How to use it:**
```bash
rag-mini research "quantum vacuum fluctuations" --deep --time 1h
```

---

## **Streaming** — Handling huge files without crashing
**What it is:** Processing large files in smaller batches instead of all at once.

**Simple explanation:** Imagine trying to eat an entire cake at once vs. eating it slice by slice. Streaming is like eating slice by slice — your computer won't choke on huge files.

---

## Common Questions

**Q: Do I need to understand embeddings to use this?**
A: Nope! Just know they help find similar code. The system handles all the technical details.

**Q: What if I don't have an embedding server?**
A: No problem! BM25 keyword search still works without one. You just don't get semantic similarity.

**Q: Should I enable query expansion?**
A: For learning new codebases: YES. For quick specific searches: NO.

**Q: Which embedding method should I choose?**
A: Use "auto" — it tries the best option and falls back gracefully if needed.

---

## Quick Start Recommendations

**For absolute beginners:**
1. Keep all default settings
2. Launch the desktop GUI: `rag-mini gui`
3. Try simple searches like "user login" or "database connection"
4. Gradually try the CLI commands as you get comfortable

**For faster results:**
- Disable query expansion
- Use specific search terms
- Use `--synthesize` only when you need AI explanations

**For learning new codebases:**
- Enable query expansion
- Use synthesis mode
- Ask "why" and "how" questions

---

This is a learning tool. Don't be afraid to experiment with settings and see what works best for your projects.
