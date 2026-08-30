"""Prompt templates for every LLM-calling node in the Self-Healing RAG graph."""

# ── Grade Documents ──────────────────────────────────────────────────────────
DOC_GRADER_PROMPT = """\
You are a document relevance grader for a RAG (Retrieval-Augmented Generation) \
system.

The query always refers to the contents of this knowledge base. The user is \
asking about these documents, not about some other subject — read it that way.

User query:
{query}

Retrieved documents:
{context}

Work in two steps, in this order.

STEP 1 — Search, and quote what you find.
Hunt through the documents for anything that could serve as, or contribute to, \
an answer: a number, a name, a heading, a bullet, a parenthetical aside, a \
line of code, a field in a structured data example. Copy the most promising \
span into "evidence" verbatim — do not paraphrase it. Leave "evidence" empty \
only if nothing in the documents relates to the query at all.

Expect the documents to use different vocabulary from the query, and expect \
the answer to appear in some form other than a plain statement. A heading or \
label naming the same thing in different terminology, a value in parentheses, \
a figure inside a data or code sample, a single item in a list, a field name \
in a structured example — any of these can answer a query. Map the query's \
intent onto whatever wording and formatting the documents actually use, rather \
than looking for the query's own phrasing.

STEP 2 — Grade, based only on step 1.
- If "evidence" is non-empty, grade "relevant".
- Grade "irrelevant" only when "evidence" is empty because the documents cover \
  entirely different subject matter.

Partial coverage counts as relevant. Do not require a complete answer — \
completeness is checked at a later step, not here.

Never describe documents you were not given. If the documents section above is \
empty, say exactly that and grade "irrelevant".

If irrelevant, state briefly in "feedback" what the documents are about instead.
"""

# ── Transform Query ──────────────────────────────────────────────────────────
QUERY_REWRITER_PROMPT = """\
You are a query rewriter for a RAG system. The previous query did not produce \
good results and needs to be improved.

Original user question (this is the true intent — stay anchored to it):
{original_query}

Previous query that was used for retrieval:
{query}

Feedback on what went wrong:
{feedback}

Rewrite the query to get better retrieval results. Focus on using different \
keywords, being more specific, or rephrasing to better match the kind of \
language likely used in the source documents.
"""

# ── Generate (first attempt) ─────────────────────────────────────────────────
GENERATE_PROMPT = """\
Answer the question based ONLY on the provided context. \
If the context does not contain enough information to fully answer the \
question, say so clearly — do not make up information.

Context:
{context}

Question:
{query}
"""

# ── Generate (retry after hallucination) ─────────────────────────────────────
GENERATE_RETRY_PROMPT = """\
Answer the question based ONLY on the provided context. \
Your previous answer was flagged with the following issue:

{feedback}

Correct this issue. Use ONLY information that is explicitly stated in the \
context below. Do not add any external knowledge.

Context:
{context}

Question:
{query}
"""

# ── Grade Answer ─────────────────────────────────────────────────────────────
ANSWER_GRADER_PROMPT = """\
You are an answer grader for a RAG system. Evaluate the generated answer on \
two criteria:

1. GROUNDING: Is every claim in the answer supported by the retrieved context? \
   The answer must not contain information that is not present in the context.
2. COMPLETENESS: Does the answer fully address the user's original question?

User question:
{original_query}

Retrieved context:
{context}

Generated answer:
{answer}

Grading rules (apply in this order):
- If the answer contains claims NOT supported by the context → grade as "hallucinated"
- If the answer is grounded but does not fully address the question → grade as "incomplete"
- If the answer is both grounded and complete → grade as "good"
"""
