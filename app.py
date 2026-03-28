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
    ]:
        if key not in st.session_state:
            st.session_state[key] = default


def _clear_file() -> None:
    st.session_state._doc_id = ""
    st.session_state._doc_label = ""


def _render_sources(ctxs: list) -> None:
    if not ctxs:
        return
    with st.expander(f"References ({len(ctxs)})", expanded=False):
        for i, ch in enumerate(ctxs, 1):
            text = str(ch.get("text", ""))
            preview = text[:600] + ("…" if len(text) > 600 else "")
            st.markdown(f"**{i}.** {preview}")


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
        st.toast("This file is already in your library. Using it now.")
    else:
        st.toast("File ready. Ask your question below.")
    return True


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

    st.markdown("## Research assistant")
    if not st.session_state.messages:
        st.caption("Ask about your research library, or attach a PDF to focus on one paper.")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant":
                _render_sources(msg.get("sources") or [])

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
            ctxs = data.get("contexts") or []
            st.markdown(answer)
            _render_sources(ctxs)

        st.session_state.messages.append(
            {"role": "assistant", "content": answer, "sources": ctxs}
        )


if __name__ == "__main__":
    main()
