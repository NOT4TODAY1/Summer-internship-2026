"""
Streamlit chat interface for the RAG Enterprise Assistant.
Talks to the FastAPI backend over HTTP so the UI and the RAG engine
can be deployed and scaled independently.
"""
import os
from datetime import datetime
from urllib.parse import quote

import httpx
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Assistant Documentaire Interne",
    page_icon="📚",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ----------------------------------------------------------------------------
# Design system
# Palette : fond papier neutre, encre ardoise pour le texte, sarcelle "vérifié"
# pour tout ce qui touche aux sources/preuves, ambre pour les signaux d'attention.
# Typo : Source Serif pour l'identité éditoriale du titre, Inter pour l'UI,
# IBM Plex Mono pour tout élément technique (modèles, ids de chunk, fichiers).
# ----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

    :root {
        --bg: #F6F7F5;
        --surface: #FFFFFF;
        --surface-alt: #EEF1EF;
        --ink: #1C2B39;
        --muted: #5B6660;
        --border: #DCE1DD;
        --accent: #0E7C7B;      /* sarcelle : sourcé / vérifié */
        --accent-soft: #E4F2F1;
        --warn: #C77D2E;        /* ambre : attention / action */
        --warn-soft: #FBEEDF;
        --danger: #B3413E;
        --danger-soft: #F8E9E8;
    }

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background: var(--bg); }

    h1 { font-family: 'Source Serif 4', serif; font-weight: 600; color: var(--ink); letter-spacing: -0.01em; }

    .app-subtitle { color: var(--muted); font-size: 0.95rem; margin-top: -0.6rem; margin-bottom: 1.2rem; }

    .mono { font-family: 'IBM Plex Mono', monospace; font-size: 0.82rem; }

    /* Sidebar status card */
    .status-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 0.85rem 1rem;
        margin-bottom: 0.75rem;
    }
    .status-row { display: flex; align-items: center; gap: 0.5rem; font-size: 0.9rem; }
    .dot { height: 8px; width: 8px; border-radius: 50%; display: inline-block; flex-shrink: 0; }
    .dot-ok { background: var(--accent); }
    .dot-bad { background: var(--danger); }

    .stat-row { display: flex; gap: 0.6rem; margin-top: 0.6rem; }
    .stat-box {
        flex: 1; background: var(--surface-alt); border-radius: 8px;
        padding: 0.5rem 0.6rem; text-align: center;
    }
    .stat-box .num { font-family: 'IBM Plex Mono', monospace; font-size: 1.05rem; color: var(--ink); font-weight: 500; }
    .stat-box .lbl { font-size: 0.7rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.03em; }

    /* Provenance ledger — signature element for source cards */
    .source-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-left: 3px solid var(--accent);
        border-radius: 6px;
        padding: 0.55rem 0.8rem;
        margin-bottom: 0.4rem;
        font-size: 0.87rem;
    }
    .source-card.low { border-left-color: var(--warn); }
    .source-card .fname { color: var(--ink); font-weight: 500; }
    .source-card .meta { color: var(--muted); font-family: 'IBM Plex Mono', monospace; font-size: 0.76rem; }
    .source-card .excerpt { color: var(--muted); font-size: 0.8rem; line-height: 1.35; margin-top: 0.35rem; }
    .conf-bar-bg { background: var(--surface-alt); border-radius: 4px; height: 5px; margin-top: 0.35rem; overflow: hidden; }
    .conf-bar-fill { height: 100%; border-radius: 4px; background: var(--accent); }
    .source-card.low .conf-bar-fill { background: var(--warn); }

    .empty-state {
        text-align: center; color: var(--muted); padding: 2.5rem 1rem;
        border: 1px dashed var(--border); border-radius: 12px; margin-top: 1rem;
    }
    .empty-state .icon { font-size: 1.8rem; }

    .timestamp { color: var(--muted); font-size: 0.72rem; margin-top: 0.2rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📚 Assistant Documentaire Interne")
st.markdown(
    '<div class="app-subtitle">Posez une question en langage naturel sur les documents de l\'entreprise — chaque réponse est sourcée.</div>',
    unsafe_allow_html=True,
)


def confidence_tier(score: float) -> str:
    """Map a relevance score to a visual tier used for the ledger accent."""
    try:
        return "high" if float(score) >= 0.7 else "low"
    except (TypeError, ValueError):
        return "low"


def render_sources(sources: list) -> None:
    """Render clickable retrieved chunks sorted by relevance."""
    if not sources:
        return
    ordered = sorted(sources, key=lambda s: s.get("relevance_score") or 0, reverse=True)
    with st.expander(f"📎 Sources ({len(ordered)})"):
        for index, s in enumerate(ordered):
            score = s.get("relevance_score") or 0
            try:
                pct = max(0.0, min(1.0, float(score))) * 100
                score_label = f"{float(score):.2f}"
            except (TypeError, ValueError):
                pct, score_label = 0, "n/a"
            tier = confidence_tier(score)
            filename = s.get("filename") or "document"
            st.markdown(
                f'<div class="source-card {tier}">'
                f'<span class="fname">{filename}</span> · '
                f'<span class="meta">{s.get("chunk_id", "")}</span>'
                f'<div class="conf-bar-bg"><div class="conf-bar-fill" style="width:{pct}%"></div></div>'
                f'<span class="meta">pertinence {score_label}</span>'
                f'<div class="excerpt">{s.get("excerpt", "")}</div></div>',
                unsafe_allow_html=True,
            )
            document_url = f"{API_URL}/documents/{quote(filename, safe='')}"
            st.link_button(
                f"📄 Ouvrir {filename}",
                document_url,
                use_container_width=True,
            )


# ----------------------------------------------------------------------------
# Sidebar — statut système
# ----------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Statut du système")

    api_ok = False
    try:
        httpx.get(f"{API_URL}/health", timeout=5).raise_for_status()
        api_ok = True
    except Exception:
        api_ok = False

    st.markdown(
        f"""
        <div class="status-card">
            <div class="status-row">
                <span class="dot {'dot-ok' if api_ok else 'dot-bad'}"></span>
                <span>{'API connectée' if api_ok else 'API non disponible'}</span>
            </div>
            <div class="mono" style="color: var(--muted); margin-top:0.3rem;">{API_URL}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if not api_ok:
        st.caption("Vérifiez que le backend FastAPI est bien lancé.")

    try:
        info = httpx.get(f"{API_URL}/collection/info", timeout=5).json()
        st.markdown(
            f"""
            <div class="status-card">
                <div class="stat-row">
                    <div class="stat-box">
                        <div class="num">{info.get('chunk_count') or 0}</div>
                        <div class="lbl">Chunks</div>
                    </div>
                </div>
                <div style="margin-top:0.6rem; font-size:0.82rem;">
                    <div class="meta mono" style="color: var(--muted);">LLM&nbsp;: {info.get('llm_model', '—')}</div>
                    <div class="meta mono" style="color: var(--muted);">Embeddings&nbsp;: {info.get('embedding_model', '—')}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    except Exception:
        pass

    st.divider()

    if st.button("🔄 Relancer l'ingestion des documents", use_container_width=True):
        with st.spinner("Ingestion en cours — cela peut prendre plusieurs minutes..."):
            try:
                resp = httpx.post(f"{API_URL}/ingest", json={"reset": True}, timeout=600)
                resp.raise_for_status()
                result = resp.json()
                st.success(
                    f"Ingestion terminée — {result.get('documents_loaded', '?')} documents, "
                    f"{result.get('chunks_indexed', '?')} chunks."
                )
            except Exception as exc:
                st.error(f"Échec de l'ingestion : {exc}")

    if st.session_state.get("messages"):
        if st.button("🗑️ Effacer la conversation", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    st.divider()
    st.caption("Assistant interne · réponses générées à partir des documents indexés uniquement.")

# ----------------------------------------------------------------------------
# Historique de conversation
# ----------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if not st.session_state.messages:
    st.markdown(
        """
        <div class="empty-state">
            <div class="icon">💬</div>
            <div style="margin-top:0.4rem;">Aucune question posée pour l'instant.</div>
            <div style="font-size:0.85rem; margin-top:0.2rem;">
                Essayez par exemple : <em>« Quelle est la procédure de remboursement des notes de frais ? »</em>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            render_sources(msg["sources"])
        if msg.get("timestamp"):
            st.markdown(f'<div class="timestamp">{msg["timestamp"]}</div>', unsafe_allow_html=True)
        if msg["role"] == "assistant" and not msg.get("is_error"):
            fb_col1, fb_col2, _ = st.columns([1, 1, 8])
            fb_key = f"fb_{i}"
            with fb_col1:
                if st.button("👍", key=f"up_{i}", help="Réponse utile"):
                    st.session_state[fb_key] = "up"
            with fb_col2:
                if st.button("👎", key=f"down_{i}", help="Réponse à améliorer"):
                    st.session_state[fb_key] = "down"
            if st.session_state.get(fb_key):
                st.caption("Merci pour votre retour ✔️" if st.session_state[fb_key] == "up" else "Retour noté, merci.")

# ----------------------------------------------------------------------------
# Saisie utilisateur
# ----------------------------------------------------------------------------
if question := st.chat_input("Ex: Quelle est la procédure de remboursement des notes de frais ?"):
    now = datetime.now().strftime("%H:%M")
    st.session_state.messages.append({"role": "user", "content": question, "timestamp": now})
    with st.chat_message("user"):
        st.markdown(question)
        st.markdown(f'<div class="timestamp">{now}</div>', unsafe_allow_html=True)

    with st.chat_message("assistant"):
        with st.spinner("Recherche dans les documents..."):
            try:
                resp = httpx.post(f"{API_URL}/query", json={"question": question}, timeout=120)
                resp.raise_for_status()
                data = resp.json()
                answer_time = datetime.now().strftime("%H:%M")
                st.markdown(data["answer"])
                render_sources(data.get("sources", []))
                st.markdown(f'<div class="timestamp">{answer_time}</div>', unsafe_allow_html=True)
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": data["answer"],
                        "sources": data.get("sources", []),
                        "timestamp": answer_time,
                    }
                )
            except httpx.HTTPStatusError as exc:
                error_msg = f"Le serveur a répondu avec une erreur ({exc.response.status_code})."
                st.error(error_msg)
                with st.expander("Détails techniques"):
                    st.code(exc.response.text or str(exc), language="text")
                st.session_state.messages.append({"role": "assistant", "content": error_msg, "is_error": True})
            except httpx.RequestError as exc:
                error_msg = "Impossible de contacter l'API — vérifiez que le backend FastAPI est démarré."
                st.error(error_msg)
                with st.expander("Détails techniques"):
                    st.code(str(exc), language="text")
                st.session_state.messages.append({"role": "assistant", "content": error_msg, "is_error": True})
            except Exception as exc:
                error_msg = f"Erreur inattendue : {exc}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg, "is_error": True})