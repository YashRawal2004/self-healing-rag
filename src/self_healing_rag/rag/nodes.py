"""Node functions for the Self-Healing RAG graph."""

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from self_healing_rag.config import EMBEDDING_MODEL, OPENROUTER_BASE_URL
from self_healing_rag.server import db

from .events import emit
from .models import AnswerGradeResponse, DocGradeResponse, RewrittenQuery
from .runtime import current_run
from .state import GraphState


def _llm(stage: str) -> ChatOpenAI:
    ctx = current_run()
    return ChatOpenAI(
        model=ctx.settings["models"][stage],
        api_key=ctx.api_key,
        base_url=OPENROUTER_BASE_URL,
        temperature=0,
    )


def _prompt(name: str) -> str:
    return current_run().settings["prompts"][name]


def retrieve(state: GraphState) -> dict:
    print(f"\n{'='*60}")
    print(f"📥 RETRIEVE — query: \"{state['query']}\"")

    ctx = current_run()
    top_k = int(ctx.settings["retrieval"]["top_k"])
    embeddings = OpenAIEmbeddings(
        model=EMBEDDING_MODEL,
        api_key=ctx.api_key,
        base_url=OPENROUTER_BASE_URL,
    )
    vector = embeddings.embed_query(state["query"])
    rows = db.search_chunks(ctx.user_id, ctx.chat_id, vector, top_k)
    context = "\n\n---\n\n".join(row["content"] for row in rows)

    print(f"   Retrieved {len(rows)} chunks ({len(context)} chars)")
    if not rows:
        print("   ⚠ No chunks in this chat — has anything been uploaded?")

    emit(
        "retrieve",
        "Searching documents",
        f"{len(rows)} chunk{'' if len(rows) == 1 else 's'} ({len(context):,} chars)"
        if rows
        else "no matches — upload a PDF in this chat",
        query=state["query"],
    )
    return {"context": context}


def grade_documents(state: GraphState) -> dict:
    print(f"\n{'='*60}")
    print("📝 GRADE DOCUMENTS")

    if not state["context"].strip():
        print("   Grade: irrelevant (no context to grade)")
        emit("grade_documents", "Grading documents", "irrelevant — nothing retrieved")
        return {
            "doc_grade": "irrelevant",
            "feedback": (
                "This chat has no retrieved documents, so there is nothing to judge. "
                "Upload a PDF to this chat first."
            ),
        }

    prompt = ChatPromptTemplate.from_template(_prompt("doc_grader"))
    grader = prompt | _llm("grade_documents").with_structured_output(DocGradeResponse)
    result: DocGradeResponse = grader.invoke({
        "query": state["original_query"],
        "context": state["context"],
    })

    print(f"   Grade: {result.grade}")
    if result.evidence:
        print(f"   Evidence: {result.evidence[:120].strip()}")
    if result.feedback:
        print(f"   Feedback: {result.feedback}")

    emit(
        "grade_documents",
        "Grading documents",
        result.grade if not result.feedback else f"{result.grade} — {result.feedback}",
        grade=result.grade,
    )
    return {"doc_grade": result.grade, "feedback": result.feedback}


def transform_query(state: GraphState) -> dict:
    print(f"\n{'='*60}")
    print("🔄 TRANSFORM QUERY")
    print(f"   Old query: \"{state['query']}\"")

    prompt = ChatPromptTemplate.from_template(_prompt("query_rewriter"))
    rewriter = prompt | _llm("transform_query").with_structured_output(RewrittenQuery)
    result: RewrittenQuery = rewriter.invoke({
        "original_query": state["original_query"],
        "query": state["query"],
        "feedback": state["feedback"],
    })

    print(f"   New query: \"{result.query}\"")
    emit(
        "transform_query",
        "Rewriting the query",
        f"“{result.query}”",
        old_query=state["query"],
        new_query=result.query,
    )
    return {"query": result.query}


def generate(state: GraphState) -> dict:
    print(f"\n{'='*60}")
    print("💡 GENERATE")

    is_retry = (
        state.get("answer_grade") == "hallucinated"
        and state.get("feedback", "") != ""
    )

    if is_retry:
        print("   (retry — using feedback-aware prompt)")
        prompt = ChatPromptTemplate.from_template(_prompt("generate_retry"))
        response = (prompt | _llm("generate")).invoke({
            "context": state["context"],
            "query": state["query"],
            "feedback": state["feedback"],
        })
    else:
        prompt = ChatPromptTemplate.from_template(_prompt("generate"))
        response = (prompt | _llm("generate")).invoke({
            "context": state["context"],
            "query": state["query"],
        })

    answer = response.content
    print(f"   Answer: {answer[:200]}{'...' if len(answer) > 200 else ''}")
    emit(
        "generate",
        "Writing the answer",
        "retry, guided by the grader's feedback" if is_retry else "from the retrieved context",
        retry=is_retry,
    )
    return {"answer": answer}


def grade_answer(state: GraphState) -> dict:
    print(f"\n{'='*60}")
    print("🎯 GRADE ANSWER")

    prompt = ChatPromptTemplate.from_template(_prompt("answer_grader"))
    grader = prompt | _llm("grade_answer").with_structured_output(AnswerGradeResponse)
    result: AnswerGradeResponse = grader.invoke({
        "original_query": state["original_query"],
        "context": state["context"],
        "answer": state["answer"],
    })

    print(f"   Grade: {result.grade}")
    if result.feedback:
        print(f"   Feedback: {result.feedback}")

    emit(
        "grade_answer",
        "Checking the answer",
        result.grade if not result.feedback else f"{result.grade} — {result.feedback}",
        grade=result.grade,
    )
    return {"answer_grade": result.grade, "feedback": result.feedback}
