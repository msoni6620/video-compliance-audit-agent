"""Streamlit UI: YouTube URL -> compliance audit report.

Run the backend first:
    uv run uvicorn backend.src.api.server:app --reload
Then the UI:
    uv run streamlit run streamlit_app.py

NOTE: the endpoint path and request/response field names are ASSUMPTIONS.
Adjust AUDIT_PATH / payload / render_report() to match backend/src/api/server.py.
"""
import requests
import streamlit as st

st.set_page_config(page_title="Video Compliance Audit", layout="wide")
st.title("Video Compliance Audit")
st.caption("Paste a YouTube link. The video is transcribed and checked against your policy documents.")

with st.sidebar:
    st.header("Backend")
    base_url = st.text_input("Base URL", "http://localhost:8000").rstrip("/")
    health_path = st.text_input("Health path", "/health")
    audit_path = st.text_input("Audit path", "/audit")
    if st.button("Check connection"):
        try:
            r = requests.get(base_url + health_path, timeout=10)
            st.success(f"Backend reachable (HTTP {r.status_code})")
        except requests.RequestException as e:
            st.error(f"Cannot reach backend: {e}")

if "reports" not in st.session_state:
    st.session_state.reports = []


def render_report(data: dict) -> None:
    """Show the report nicely if it has common keys, else fall back to raw JSON."""
    status = data.get("status") or data.get("overall_status") or data.get("verdict")
    if status:
        s = str(status).lower()
        if any(w in s for w in ("fail", "non", "violat")):
            st.error(f"Overall status: {status}")
        elif any(w in s for w in ("pass", "compliant")):
            st.success(f"Overall status: {status}")
        else:
            st.info(f"Overall status: {status}")

    summary = data.get("summary") or data.get("final_report") or data.get("report")
    if summary:
        st.subheader("Summary")
        st.write(summary)

    findings = data.get("violations") or data.get("findings") or data.get("issues")
    if findings:
        st.subheader("Findings")
        if isinstance(findings, list) and findings and isinstance(findings[0], dict):
            st.dataframe(findings, use_container_width=True)
        else:
            for item in findings if isinstance(findings, list) else [findings]:
                st.write(f"- {item}")

    transcript = data.get("transcript")
    if transcript:
        with st.expander("Transcript"):
            st.write(transcript)

    with st.expander("Raw response"):
        st.json(data)


url = st.text_input("YouTube URL", placeholder="https://www.youtube.com/watch?v=...")

if st.button("Run audit", type="primary", disabled=not url.strip()):
    with st.spinner("Downloading, transcribing, and checking policies. This can take a few minutes..."):
        try:
            resp = requests.post(base_url + audit_path, json={"video_url": url.strip()}, timeout=1800)
        except requests.RequestException as e:
            st.error(f"Request failed: {e}")
        else:
            if resp.ok:
                try:
                    data = resp.json()
                    st.session_state.reports.append((url.strip(), data))
                    render_report(data)
                except ValueError:
                    st.code(resp.text)
            else:
                st.error(f"Backend returned HTTP {resp.status_code}")
                st.code(resp.text)

if st.session_state.reports:
    st.divider()
    st.subheader("Earlier audits this session")
    for past_url, past in reversed(st.session_state.reports[:-1]):
        with st.expander(past_url):
            render_report(past)