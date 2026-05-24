from __future__ import annotations

import os

import httpx
import streamlit as st

DEFAULT_API = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

_CSS = """
<style>
    .block-container { padding-top: 1rem; padding-bottom: 2rem; max-width: 42rem; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stToolbar"] {display: none;}
    [data-testid="stDecoration"] {display: none;}
    [data-testid="stDeployButton"] {display: none;}
    div[data-testid="stChatMessage"] { padding: 0.55rem 0.75rem; }

    div[data-testid="stPopover"] > button {
        min-width: 5.25rem; white-space: nowrap;
    }
    .file-pill {
        display: inline-flex; align-items: center; gap: 0.45rem;
        background: #eceff4; border-radius: 999px; padding: 0.2rem 0.65rem;
        font-size: 0.85rem; color: #1e1e1e;
    }
</style>
"""


def _api() -> str:
    return (st.session_state.get("_api_url") or DEFAULT_API).rstrip("/")


def _http(base: str | None = None) -> httpx.Client:
    return httpx.Client(base_url=base or _api(), timeout=120.0)


def _boot() -> None:
    for key, default in [
        ("messages", []),
        ("_doc_id", ""),
        ("_doc_label", ""),
        ("_api_url", DEFAULT_API),
        ("_is_processing", False),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default


def _clear_file() -> None:
    st.session_state._doc_id = ""
    st.session_state._doc_label = ""
    st.session_state._is_processing = False


def _render_citations(citations: list) -> None:
    if not citations:
        return
    with st.expander(f"View {len(citations)} Source Citations", expanded=False):
        for c in citations:
            doc_name = c.get("document_name", "Unknown")
            page = c.get("page", "N/A")
            score = c.get("score", 0.0)
            chunk_id = c.get("chunk_id", "N/A")
            text = str(c.get("text", ""))
            
            st.markdown(f"### [{c.get('id')}] {doc_name}")
            col1, col2, col3 = st.columns(3)
            col1.metric("Page", page)
            
            try:
                formatted_score = f"{float(score):.3f}"
            except (ValueError, TypeError):
                formatted_score = score
                
            col2.metric("Relevance Score", formatted_score)
            col3.metric("Chunk ID", chunk_id)
            
            st.info(text)
            st.divider()


def _attach_panel(api_base: str) -> None:
    """Full-width area inside popover so the uploader never sits in a 1px column."""
    st.caption("PDF only")
    f = st.file_uploader(
        "Upload",
        type=["pdf"],
        key="_attach_pdf_widget",
        label_visibility="collapsed",
    )
    st.checkbox(
        "Replace if this exact file was added before",
        key="_attach_force_replace",
        value=False,
    )
    if st.button("Add file", type="primary", use_container_width=True, key="_attach_confirm"):
        if f is None:
            st.warning("Choose a file first.")
            return
        force = bool(st.session_state.get("_attach_force_replace", False))
        ok = _upload_pdf_with_force(f, api_base, force)
        if ok:
            st.rerun()


def _upload_pdf_with_force(file_obj, api_base: str, force: bool) -> bool:
    try:
        with st.spinner("Processing your file…"):
            with _http(api_base) as c:
                r = c.post(
                    "/ingest/upload",
                    files={
                        "file": (
                            file_obj.name or "paper.pdf",
                            file_obj.getvalue(),
                            "application/pdf",
                        )
                    },
                    data={"force": "true" if force else "false"},
                )
                r.raise_for_status()
                data = r.json()
    except httpx.HTTPStatusError as e:
        detail = ""
        try:
            body = e.response.json()
            if isinstance(body, dict) and body.get("detail"):
                detail = str(body["detail"])
        except Exception:
            detail = (e.response.text or "")[:200]
        st.toast("Could not add this file.")
        if detail:
            st.caption(detail)
        return False
    except Exception as e:
        st.toast("Could not reach the service.")
        st.caption(str(e)[:200])
        return False

    did = data.get("doc_id")
    if not did:
        st.toast("Upload returned no document. Try again.")
        return False

    st.session_state._doc_label = file_obj.name or "Uploaded file"
    st.session_state._doc_id = str(did)
    if data.get("status") == "duplicate":
        st.session_state._is_processing = False
        st.toast("This file is already in your library. Using it now.")
    elif data.get("status") == "processing":
        st.session_state._is_processing = True
        st.toast("File is being processed in background. You can keep chatting.")
    else:
        st.session_state._is_processing = False
        st.toast("File ready. Ask your question below.")
    return True

@st.fragment(run_every="3s")
def _processing_status_fragment(doc_id: str, api_base: str):
    if not doc_id or not st.session_state.get("_is_processing"):
        return
        
    try:
        with _http(api_base) as c:
            r = c.get(f"/ingest/status/{doc_id}")
            if r.status_code == 200:
                data = r.json()
                status = data.get("status")
                progress = data.get("progress", 0)
                msg = data.get("message", "")
                
                if status == "processing":
                    st.info(f"{msg}")
                    st.progress(progress / 100.0)
                elif status == "completed":
                    st.success(f"{msg}")
                    st.session_state._is_processing = False
                    st.rerun()
                elif status == "failed":
                    st.error(f"{msg}")
                    st.session_state._is_processing = False
                    st.rerun()
            else:
                st.warning(f"Status check returned {r.status_code}")
    except Exception as e:
        st.error(f"Fragment error: {str(e)}")


def main() -> None:
    _boot()

    try:
        st.set_page_config(
            page_title="Research assistant",
            layout="centered",
            initial_sidebar_state="collapsed",
            menu_items={
                "Get Help": None,
                "Report a bug": None,
                "About": None,
            },
        )
    except TypeError:
        st.set_page_config(
            page_title="Research assistant",
            layout="centered",
            initial_sidebar_state="collapsed",
        )

    st.markdown(_CSS, unsafe_allow_html=True)

    with st.sidebar:
        st.caption("Settings")
        st.text_input("API address", key="_api_url")
        if st.button("Test connection"):
            try:
                with _http() as c:
                    c.get("/health").raise_for_status()
                st.success("Connected")
            except Exception as e:
                st.error(str(e))
        st.divider()
        if st.button("New chat", use_container_width=True):
            st.session_state.messages = []
            _clear_file()
            st.rerun()

    api_base = _api()

    st.markdown("## AI Research Assistant Platform")
    st.caption("Hybrid Retrieval • Citation Tracing • Retrieval Observability")
    st.divider()
    
    if not st.session_state.messages:
        st.info("Ask about your research library, or attach a PDF to focus on one paper.")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant":
                _render_citations(msg.get("citations") or [])

    last_debug = None
    for msg in reversed(st.session_state.messages):
        if msg["role"] == "assistant" and msg.get("debug"):
            last_debug = msg["debug"]
            break
            
    if last_debug:
        with st.sidebar:
            st.divider()
            st.subheader("Retrieval Debug")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Cache Status", "HIT" if last_debug.get("cache_hit") else "MISS")
                st.metric("Ret. Mode", last_debug.get("retrieval_mode", "unknown"))
            with col2:
                st.metric("Top K", last_debug.get("top_k", 0))
                st.metric("Total Latency", f"{last_debug.get('total_ms', 0)} ms")
            
            st.markdown("#### Latency Breakdown")
            c1, c2 = st.columns(2)
            with c1:
                st.metric("Embedding Time", f"{last_debug.get('embedding_ms', 0)} ms")
            with c2:
                st.metric("Retrieval Time", f"{last_debug.get('retrieval_ms', 0)} ms")
            
            st.metric("LLM Generation", f"{last_debug.get('llm_ms', 0)} ms")

    doc_id = (st.session_state._doc_id or "").strip()
    doc_label = (st.session_state._doc_label or "").strip()

    bar_l, bar_r = st.columns([2, 10])
    with bar_l:
        popover_fn = getattr(st, "popover", None)
        if popover_fn:
            with popover_fn("Attach"):
                _attach_panel(api_base)
        else:
            with st.expander("Attach PDF", expanded=False):
                _attach_panel(api_base)
    with bar_r:
        if doc_label:
            c1, c2 = st.columns([6, 1])
            with c1:
                st.markdown(f'<span class="file-pill">{doc_label}</span>', unsafe_allow_html=True)
            with c2:
                if st.button("Clear", key="_remove_file"):
                    _clear_file()
                    st.rerun()
                    
    if st.session_state.get("_is_processing") and doc_id:
        _processing_status_fragment(doc_id, api_base)

    if prompt := st.chat_input("Ask a question…"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner(""):
                try:
                    body: dict = {"query": prompt.strip(), "auto_expand_corpus": True}
                    if doc_id:
                        body["document_id"] = doc_id
                    with _http(api_base) as c:
                        r = c.post("/chat/", json=body)
                        r.raise_for_status()
                        data = r.json()
                except Exception:
                    data = {
                        "answer": "Something went wrong. Check your connection and try again.",
                        "contexts": [],
                    }

            answer = data.get("answer") or ""
            citations = data.get("citations") or []
            debug = data.get("debug") or {}
            st.markdown(answer)
            _render_citations(citations)

        st.session_state.messages.append(
            {"role": "assistant", "content": answer, "citations": citations, "debug": debug}
        )
        st.rerun()


if __name__ == "__main__":
    main()
