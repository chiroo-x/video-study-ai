import os
import re
import subprocess
import tempfile
from pathlib import Path

import streamlit as st
import yt_dlp
from groq import Groq

APP_TITLE = "Video Study AI"
MAX_AUDIO_MB = 20  # Stay below common transcription upload limits.
TRANSCRIPTION_MODEL = "whisper-large-v3-turbo"
GENERATION_MODEL = "llama-3.3-70b-versatile"

st.set_page_config(page_title=APP_TITLE, page_icon="🎓", layout="centered")
st.title("Video Study AI")
st.write("Turn a video into quizzes, summaries, flashcards, and study notes.")
st.info(
    "This online demo uses Groq for AI processing. You need a Groq API key. "
    "Your key is used for this session and is not saved by this app."
)

with st.sidebar:
    st.header("AI settings")
    api_key = st.text_input(
        "Groq API key",
        type="password",
        help="Create a key at https://console.groq.com/keys. Do not share it with anyone."
    )
    generation_model = st.text_input("Text model", value=GENERATION_MODEL)
    st.caption("Model availability and free-tier limits can change.")

st.subheader("1. Choose a video")
source = st.radio("Video source", ["Upload a video/audio file", "YouTube URL"], horizontal=True)
uploaded_file = None
youtube_url = ""

if source == "Upload a video/audio file":
    uploaded_file = st.file_uploader(
        "Select a file",
        type=["mp4", "mov", "mkv", "webm", "avi", "m4v", "mp3", "wav", "m4a", "flac", "mpeg", "mpga"],
        help="For best results, use a video with clear speech. Large files may take longer."
    )
else:
    youtube_url = st.text_input("YouTube link", placeholder="https://www.youtube.com/watch?v=...")
    st.caption("Only process videos you have permission to access. Some videos may be unavailable.")

st.subheader("2. What should the AI do?")
instruction = st.text_area(
    "Your instructions",
    value=(
        "Create exactly 27 multiple-choice quiz questions based only on this video. "
        "Give each question four options (A-D), identify the correct answer, and explain it briefly. "
        "Cover the important ideas across the whole video and avoid repeated questions."
    ),
    height=150,
)

def run_ffmpeg(args):
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "Unknown FFmpeg error")[-1500:]
        raise RuntimeError("Audio conversion failed. " + detail)

def download_youtube(url: str, folder: str) -> str:
    template = str(Path(folder) / "source.%(ext)s")
    options = {
        "format": "bestaudio/best",
        "outtmpl": template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download([url])
    candidates = [p for p in Path(folder).glob("source.*") if p.is_file()]
    if not candidates:
        raise RuntimeError("Could not retrieve audio from this URL. The video may be restricted or unavailable.")
    return str(max(candidates, key=lambda p: p.stat().st_size))

def make_audio_chunks(input_path: str, folder: str):
    # Encode mono MP3 at a low bitrate and split into 8-minute chunks to keep uploads small.
    pattern = str(Path(folder) / "chunk_%03d.mp3")
    run_ffmpeg([
        "ffmpeg", "-y", "-i", input_path, "-vn", "-ac", "1", "-ar", "16000",
        "-b:a", "48k", "-f", "segment", "-segment_time", "480",
        "-reset_timestamps", "1", pattern
    ])
    chunks = sorted(Path(folder).glob("chunk_*.mp3"))
    if not chunks:
        raise RuntimeError("No audio could be extracted from this file.")
    for chunk in chunks:
        size_mb = chunk.stat().st_size / (1024 * 1024)
        if size_mb > MAX_AUDIO_MB:
            raise RuntimeError(
                f"An audio segment is {size_mb:.1f} MB, too large for this demo. "
                "Try a shorter video or lower audio quality."
            )
    return chunks

def transcribe_chunks(client, chunks):
    transcript_parts = []
    for i, chunk in enumerate(chunks, start=1):
        st.write(f"Transcribing audio segment {i} of {len(chunks)}…")
        with open(chunk, "rb") as audio_file:
            result = client.audio.transcriptions.create(
                file=(chunk.name, audio_file.read()),
                model=TRANSCRIPTION_MODEL,
                response_format="verbose_json",
            )
        text = getattr(result, "text", "") or ""
        if text.strip():
            transcript_parts.append(f"[Segment {i}]\n{text.strip()}")
    transcript = "\n\n".join(transcript_parts)
    if not transcript:
        raise RuntimeError("No speech was detected, or transcription returned an empty result.")
    return transcript

def generate_result(client, model, instructions, transcript):
    # Avoid overflowing model context on very long videos. The user is told if this occurs.
    limit = 65000
    clipped = len(transcript) > limit
    text_for_model = transcript[:limit]
    prompt = f"""You are a careful study assistant. Follow the user's instructions using only the supplied transcript.
Do not invent facts, quotations, or details not supported by the transcript.
If the user asks for a specific number of questions, produce exactly that number where the source supports it.
Use clear headings and readable formatting. Do not claim to have seen visual details; only a transcript is provided.

USER INSTRUCTIONS:
{instructions}

VIDEO TRANSCRIPT:
{text_for_model}

Complete the user's instructions now."""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You create accurate, source-grounded study materials."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content or "", clipped

if st.button("Generate study material", type="primary", use_container_width=True):
    if not api_key.strip():
        st.error("Enter your Groq API key in the sidebar first.")
        st.stop()
    if not instruction.strip():
        st.error("Enter instructions for the AI.")
        st.stop()
    if source == "Upload a video/audio file" and uploaded_file is None:
        st.error("Upload a video or audio file first.")
        st.stop()
    if source == "YouTube URL" and not youtube_url.strip():
        st.error("Paste a YouTube URL first.")
        st.stop()

    try:
        client = Groq(api_key=api_key.strip())
        with tempfile.TemporaryDirectory(prefix="video_study_ai_") as temp:
            temp_dir = Path(temp)
            if source == "Upload a video/audio file":
                suffix = Path(uploaded_file.name).suffix or ".mp4"
                input_path = temp_dir / f"uploaded{suffix}"
                input_path.write_bytes(uploaded_file.getbuffer())
                input_path = str(input_path)
            else:
                if not re.match(r"^https?://", youtube_url.strip(), flags=re.I):
                    st.error("Enter a URL beginning with http:// or https://.")
                    st.stop()
                with st.spinner("Retrieving YouTube audio…"):
                    input_path = download_youtube(youtube_url.strip(), str(temp_dir))

            with st.spinner("Extracting and splitting audio…"):
                chunks = make_audio_chunks(input_path, str(temp_dir))

            with st.status("Transcribing speech…", expanded=True) as status:
                transcript = transcribe_chunks(client, chunks)
                status.update(label="Transcription complete", state="complete", expanded=False)

            with st.spinner("Generating your result…"):
                result, clipped = generate_result(client, generation_model.strip(), instruction, transcript)

            st.session_state["result"] = result
            st.session_state["transcript"] = transcript
            st.session_state["clipped"] = clipped
            st.success("Your study material is ready.")
    except Exception as e:
        message = str(e)
        if "401" in message or "authentication" in message.lower():
            st.error("The API key was rejected. Check that your Groq API key is correct.")
        else:
            st.error(f"Processing failed: {message}")
        st.caption("If you get a rate-limit or model error, check your Groq console for current limits and available models.")

if st.session_state.get("result"):
    st.subheader("3. Your result")
    if st.session_state.get("clipped"):
        st.warning("This transcript was very long; only part of it was sent to the text model. Long-video summarization can be improved in a future version.")
    st.markdown(st.session_state["result"])
    st.download_button(
        "Download result (.txt)",
        data=st.session_state["result"],
        file_name="video_study_result.txt",
        mime="text/plain",
        use_container_width=True,
    )
    with st.expander("View transcript"):
        st.text_area("Transcribed speech", st.session_state.get("transcript", ""), height=300)

st.divider()
st.caption(
    "Privacy note: the video/audio is processed by this hosted app and sent to the selected AI provider for transcription. "
    "Do not upload confidential or sensitive material. This app does not save API keys to a database."
)
