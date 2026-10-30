"""Python-only Streamlit frontend for VisionVoice AI."""
import os
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
MAX_UPLOAD_MB = max(1, int(os.getenv("MAX_UPLOAD_MB", "10")))

st.set_page_config(page_title="VisionVoice AI", page_icon="✨", layout="centered")
st.title("✨ VisionVoice AI")
st.caption("A Python multimodal assistant for text, image understanding, and audio insights — powered by Gemini.")

with st.sidebar:
    st.subheader("VisionVoice AI")
    st.write("A Python-only assistant that turns text, pictures, and recordings into useful answers.")
    st.info(f"Maximum upload size: {MAX_UPLOAD_MB} MB per file")
    st.caption("Uploaded media is sent to Google Gemini for analysis. Do not upload private or sensitive files.")
    if st.button("Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_input" not in st.session_state:
    st.session_state.pending_input = ""

for item in st.session_state.messages:
    with st.chat_message(item["role"]):
        st.markdown(item["content"])
        if item.get("attachment"):
            st.caption(f"📎 {item['attachment']}")

st.divider()
st.subheader("Start a conversation")
modality = st.radio("Input type", ["Text", "Image", "Audio"], horizontal=True)
mode = modality.lower()
answer_style = st.selectbox(
    "Answer style",
    ["Balanced", "Brief", "Detailed"],
    help="Choose how much explanation the assistant should provide.",
)
attachment = None
if mode == "image":
    attachment = st.file_uploader("Choose an image", type=["jpg", "jpeg", "png", "webp"], key="image_upload")
    if attachment is not None:
        st.image(attachment, caption=attachment.name, use_container_width=True)
elif mode == "audio":
    attachment = st.file_uploader(
        "Choose an audio clip",
        type=["wav", "mp3", "ogg", "webm", "m4a", "mp4", "aac", "flac"],
        key="audio_upload",
    )
    if attachment is not None:
        st.audio(attachment)

prompt = st.text_area(
    "Your message" if mode == "text" else "Question about this file (optional)",
    value=st.session_state.pending_input,
    placeholder="e.g. Explain this in simple words…" if mode == "text" else "e.g. What objects are visible?",
    height=100,
)
send = st.button(
    "Send message",
    type="primary",
    use_container_width=True,
    disabled=(mode == "text" and not prompt.strip()) or (mode != "text" and attachment is None),
)

if send:
    user_text = prompt.strip()
    style_instruction = {
        "Balanced": "Give a clear, helpful answer.",
        "Brief": "Answer briefly using only the most important points.",
        "Detailed": "Give a detailed, step-by-step explanation with examples when useful.",
    }[answer_style]
    user_text = f"{style_instruction}\n\n{user_text}" if user_text else style_instruction
    st.session_state.pending_input = prompt.strip()
    label = f"{modality} · {attachment.name}" if attachment is not None else "Text"
    display_text = prompt.strip() or (
        "Please describe this image." if mode == "image" else
        "Please summarize this audio." if mode == "audio" else ""
    )
    st.session_state.messages.append({
        "role": "user",
        "content": display_text,
        "attachment": label if attachment else None,
    })
    with st.chat_message("user"):
        st.markdown(display_text)
        if attachment:
            st.caption(f"📎 {label}")

    try:
        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                data = {"modality": mode, "message": user_text}
                files = None
                if attachment is not None:
                    files = {"file": (attachment.name, attachment.getvalue(), attachment.type)}
                response = requests.post(
                    f"{BACKEND_URL}/api/chat", data=data, files=files, timeout=120
                )
                if response.status_code >= 400:
                    try:
                        detail = response.json().get("detail", "The request could not be completed.")
                    except ValueError:
                        detail = "The backend returned an unexpected response."
                    raise RuntimeError(detail)
                answer = response.json().get("text", "").strip()
                if not answer:
                    raise RuntimeError("The AI returned an empty response. Please retry.")
                st.markdown(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})
        st.session_state.pending_input = ""
    except requests.Timeout:
        error = "The request timed out. Your message is still available; please try again."
        with st.chat_message("assistant"):
            st.error(error)
        st.session_state.messages.append({"role": "assistant", "content": f"⚠️ {error}"})
    except requests.ConnectionError:
        error = "Cannot connect to the backend. Start FastAPI in a second terminal and retry."
        with st.chat_message("assistant"):
            st.error(error)
        st.session_state.messages.append({"role": "assistant", "content": f"⚠️ {error}"})
    except (RuntimeError, ValueError) as exc:
        error = str(exc)
        with st.chat_message("assistant"):
            st.error(error)
        st.session_state.messages.append({"role": "assistant", "content": f"⚠️ {error}"})
    st.rerun()

st.caption("VisionVoice AI is an educational demo. Verify important information independently.")
