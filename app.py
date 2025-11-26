# YouSummarizer - Dark Neon Red + YouTube Logo (Option B - Full replacement)
# Full copy-paste Streamlit app with all UI labels replaced by <h3 class="section-title"> headings

import os
import tempfile
import shutil
import requests
import yt_dlp
import streamlit as st
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai
import logging

try:
    from reportlab.pdfgen import canvas
    PDF_AVAILABLE = True
except Exception:
    PDF_AVAILABLE = False

try:
    from docx import Document
    DOCX_AVAILABLE = True
except Exception:
    DOCX_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(os.path.join(os.getcwd(), ".env"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GENAI_API_KEY") or os.getenv("GOOGLE_API_KEY")
YT_API_KEY = os.getenv("YT_API_KEY") or os.getenv("YOUTUBE_API_KEY") or os.getenv("YOUTUBE_API")

# ------------------ UI THEME (NEON RED) ------------------
st.set_page_config(page_title="YouSummarizer", layout="wide")

st.markdown("""
<style>

:root {
    --glass-bg: rgba(22, 22, 22, 0.55);
    --border-soft: rgba(255, 255, 255, 0.10);
    --neon: #ff2b2b;
    --neon-glow: 0px 0px 12px rgba(255, 50, 50, 0.8);
}

/* Background */
.stApp {
    background: linear-gradient(145deg, #050505, #111111, #1a1a1a);
    color: white !important;
}

/* Title */
h1 {
    text-align: center !important;
    font-weight: 800 !important;
    color: white !important;
    margin-top: -10px;
    text-shadow: var(--neon-glow);
}

/* Section Titles (h3) */
.section-title {
    font-size: 26px !important;
    font-weight: 700 !important;
    color: white !important;
    margin-top: 1px !important;
    margin-bottom: 0px !important;
    text-shadow: var(--neon-glow);
}
.summary-title {
    font-size: 30px !important;
    font-weight: 700 !important;
    color: white !important;
    margin-top: 1px !important;
    margin-bottom: 0px !important;
    text-shadow:None;
    
}


/* Glass Buttons */
.stButton>button {
    background: rgba(50, 50, 50, 0.55);
    border: 1px solid var(--border-soft);
    color: white;
    padding: 12px 32px;
    font-size: 19px;
    border-radius: 14px;
    transition: 0.25s;
    backdrop-filter: blur(8px);
}
.stButton>button:hover {
    background: var(--neon);
    color: black !important;
    transform: translateY(-2px) scale(1.05);
    box-shadow: var(--neon-glow);
}

/* Inputs */
input, textarea, select, .stTextInput>div>div>input {
    border-radius: 12px !important;
    background: rgba(40,40,40,0.55) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    color: white !important;
    backdrop-filter: blur(6px);
}


/* Expander */
.streamlit-expanderHeader {
    background: rgba(30,30,30,0.55) !important;
    border-radius: 12px !important;
    border: 1px solid var(--border-soft) !important;
    color: white !important;
}
.streamlit-expanderContent {
    background: rgba(20,20,20,0.5) !important;
}

/* Radio + Select */
.stSelectbox, .stRadio {
    padding: 12px 16px;
    border-radius: 14px;
    background: rgba(25,25,25,0.45);
    border: 1px solid rgba(255,255,255,0.07);
    backdrop-filter: blur(6px);
}

/* Center Button */
.center-btn {
    display: flex;
    justify-content: center;
    margin-top: 12px;
}

/* Download Buttons */
.download-btn-center {
    display: flex;
    justify-content: center;
    margin-bottom: 10px;
}

/* Progress Glow */
.css-18ni7ap {
    box-shadow: var(--neon-glow);
}

</style>
""", unsafe_allow_html=True)


# ------------------ YOUTUBE LOGO + TITLE ------------------

st.markdown("""
<div style="display:flex; justify-content:center; align-items:center; gap:14px; margin-top:5px;">
    <img src="https://goodly.co.in/wp-content/uploads/2023/10/youtube-logo-png-46016-1.png"
         style="width:120px; margin-top:4px;">
    <h1 style="margin:0; line-height:3; font-height:70px;">YouTube Video Summarizer</h1>
</div>
""", unsafe_allow_html=True)

# ------------------ MODEL SETUP ------------------
if not GEMINI_API_KEY:
    st.error("❌ GEMINI_API_KEY missing in .env file.")
else:
    genai.configure(api_key=GEMINI_API_KEY)

if not YT_API_KEY:
    st.info("⚠️ YT_API_KEY missing — Search disabled.")

if GEMINI_API_KEY:
    SUMMARY_MODEL = genai.GenerativeModel("models/gemini-2.5-flash")
    AUDIO_MODEL = genai.GenerativeModel("models/gemini-2.5-flash")
else:
    SUMMARY_MODEL = None
    AUDIO_MODEL = None


# ------------------------------------------------------
# ✅✅✅ LOGIC BELOW REMAINS EXACTLY THE SAME ✅✅✅
# (Extraction, Transcript, Chunking, Summary, Downloads)
# ------------------------------------------------------

# ✅ Extract video ID
def extract_video_id(url: str):
    if not url:
        return None
    url = url.strip()
    if "v=" in url:
        return url.split("v=")[1].split("&")[0]
    if "youtu.be" in url:
        return url.split("/")[-1].split("?")[0]
    if len(url) == 11 and "/" not in url:
        return url
    return None

# ✅ Search
def search_youtube(query, max_results=6):
    if not YT_API_KEY or not query:
        return []
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {"part": "snippet","q": query,"type": "video","maxResults": max_results,"key": YT_API_KEY}
    r = requests.get(url, params=params)
    data = r.json()
    results = []
    for it in data.get("items", []):
        vid = it["id"].get("videoId")
        snip = it.get("snippet", {})
        results.append({
            "videoId": vid,
            "title": snip.get("title", "Unknown Title"),
            "channelTitle": snip.get("channelTitle", "Unknown Channel"),
            "thumbnail": snip.get("thumbnails", {}).get("medium", {}).get("url"),
            "url": f"https://www.youtube.com/watch?v={vid}"
        })
    return results

# ✅ Metadata fetch
def get_video_metadata(video_id):
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {"part": "snippet", "id": video_id, "key": YT_API_KEY}
    r = requests.get(url, params=params)
    data = r.json()
    items = data.get("items", [])
    if items:
        snip = items[0]["snippet"]
        return (
            snip.get("title", "Unknown Title"),
            snip.get("channelTitle", "Unknown Channel"),
            snip.get("thumbnails", {}).get("high", {}).get("url"),
        )
    return "Unknown Title", "Unknown Channel", None

# ✅ Transcript retrieval
def fetch_transcript(video_id, lang_pref):
    langs = ["hi", "en"] if lang_pref == "Hindi" else ["en", "hi"]
    try:
        data = YouTubeTranscriptApi.get_transcript(video_id, languages=langs)
        return " ".join([x["text"] for x in data])
    except:
        return None

# ✅ Audio download + transcription
def download_audio_to_mp3(url):
    tmpdir = tempfile.mkdtemp()
    base_path = os.path.join(tmpdir, "audio")
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": base_path + ".%(ext)s",
        "quiet": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "128",
        }],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    mp3_path = base_path + ".mp3"
    if os.path.exists(mp3_path):
        return mp3_path, tmpdir
    raise Exception("Audio download failed")

def auto_transcribe_audio(url, lang_pref):
    mp3_path, tmpdir = download_audio_to_mp3(url)
    upload = genai.upload_file(mp3_path)
    prompt = (
        "Transcribe this audio to text in Hindi."
        if lang_pref == "Hindi"
        else "Transcribe this audio to text in English."
    )
    response = AUDIO_MODEL.generate_content([prompt, upload])
    shutil.rmtree(tmpdir)
    return getattr(response, 'text', None)

# ✅ Chunk + summarize
def chunk_text(text, max_chars=15000):
    chunks = []
    start = 0
    L = len(text)
    while start < L:
        end = min(start + max_chars, L)
        chunks.append(text[start:end].strip())
        start = end
    return chunks

def summarize_text(text, progress_obj=None, status_obj=None):
    if not text or len(text.strip()) < 10:
        return None, None, "🚫 No spoken words detected."
    chunks = chunk_text(text, max_chars=15000)
    total_chunks = len(chunks)
    chunk_summaries = []
    for i, chunk in enumerate(chunks):
        prompt = f"Provide a detailed explanation and then bullet points:\n\n{chunk}"
        resp = SUMMARY_MODEL.generate_content(prompt)
        chunk_summaries.append(getattr(resp, "text", ""))
        if progress_obj:
            progress_obj.progress(60 + int(35 * ((i + 1) / total_chunks)))
    combined = "\n\n".join(chunk_summaries)
    detailed = getattr(SUMMARY_MODEL.generate_content("Combine into a detailed explanation:\n\n" + combined), "text", "")
    keypoints = getattr(SUMMARY_MODEL.generate_content("Provide bullet points using • bullets:\n\n" + combined), "text", "")
    if progress_obj:
        progress_obj.progress(100)
    return detailed, keypoints, None


# ---------------- UI FLOW (Full replacement style) ----------------

# Input method section (h3 replaces the label)
st.markdown('<h3 class="section-title">Choose Input Method</h3>', unsafe_allow_html=True)
input_method = st.selectbox("", ["URL Only", "Search Only", "Both (Recommended)"], index=2)

if "url_input" not in st.session_state:
    st.session_state.url_input = ""

results = []

# SEARCH AREA (h3 replaces label)
if input_method in ["Search Only", "Both (Recommended)"]:
    st.markdown('<h3 class="section-title">Search YouTube</h3>', unsafe_allow_html=True)

    search_query = st.text_input("", key="search_query")

    st.markdown('<div class="center-btn">', unsafe_allow_html=True)
    search_click = st.button("Search")
    st.markdown('</div>', unsafe_allow_html=True)

    if search_click:
        results = search_youtube(search_query)
        if not results:
            st.warning("No results found.")
    if results:
        titles = [f"{r['title']} — {r['channelTitle']}" for r in results]
        selected = st.radio("", titles)
        idx = titles.index(selected)
        new_url = results[idx]["url"]
        if new_url != st.session_state.url_input:
            st.session_state.url_input = new_url
            st.rerun()

# URL INPUT (h3 replaces label)
if input_method in ["URL Only", "Both (Recommended)"]:
    st.markdown('<h3 class="section-title">Paste YouTube URL</h3>', unsafe_allow_html=True)
    st.text_input("", key="url_input")

final_url = st.session_state.url_input
video_id = extract_video_id(final_url)

# SUMMARY OPTIONS GROUP (h3 replaces the section label)
st.markdown('<h3 class="section-title">Summary Options</h3>', unsafe_allow_html=True)
with st.expander("", expanded=True):
    colA, colB = st.columns(2)
    with colA:
        st.markdown('<h3  >Select Summary Type</h3>', unsafe_allow_html=True)
        summary_type = st.selectbox("", ["🧾 Both (Recommended)", "📖 Detailed Only", "⭐ Point-to-Point Only"], index=0)
    with colB:
        st.markdown('<h3 >Select Raw Transcript Language</h3>', unsafe_allow_html=True)
        summary_language = st.selectbox("", ["English", "Hindi"], index=0)

# GENERATE BUTTON (keep the button text)
st.markdown('<div class="center-btn">', unsafe_allow_html=True)
generate = st.button("🚀 Generate Summary")
st.markdown('</div>', unsafe_allow_html=True)

# PROCESSING
if generate:
    if not final_url or not video_id:
        st.error("⚠️ Provide a URL or choose from search.")
        st.stop()

    title, channel, thumbnail = get_video_metadata(video_id)

    
    
    st.markdown(f"<p style='text-align:center;'><img src='{thumbnail}' width='1200' height='700'></p>", unsafe_allow_html=True)

    

    st.write(f"**🎞 Title:** {title}")
    st.write(f"**📺 Channel:** {channel}")

    progress = st.progress(0)
    status = st.empty()

    status.write("📜 Retrieving transcript…")
    progress.progress(15)

    transcript = fetch_transcript(video_id, summary_language)

    if not transcript:
        st.info("🎤 No transcript found. Attempting audio transcription…")
        status.write("🎤 Transcribing audio…")
        progress.progress(35)
        transcript = auto_transcribe_audio(final_url, summary_language)
        if not transcript:
            st.error("Unable to retrieve transcript.")
            st.stop()

    with st.expander("View raw transcript (click to expand)", expanded=False):
        st.text_area("Raw Transcript", value=transcript[:100000], height=350)

    status.write("🧠 Generating summaries…")
    progress.progress(60)

    detailed, keypoints, err = summarize_text(
        transcript,
        progress_obj=progress,
        status_obj=status
    )

    if err:
        st.error(err)
        st.stop()

    status.write("✅ Completed!")
    st.success("✅ Summary Ready!")

    combined = ""

    if summary_type in ["🧾 Both (Recommended)", "📖 Detailed Only"]:
        st.subheader("📝 Detailed Summary")
        st.write(detailed)
        combined += "DETAILED SUMMARY:\n\n" + detailed + "\n\n\n"

    if summary_type in ["🧾 Both (Recommended)", "⭐ Point-to-Point Only"]:
        st.subheader("⭐ Key Points Summary")
        st.write(keypoints)
        combined += "KEY POINTS SUMMARY:\n\n" + keypoints + "\n"

    # DOWNLOAD AREA (h3 heading for download area)
    st.markdown('<h3 class="section-title">Download Summary</h3>', unsafe_allow_html=True)
    with st.expander("", expanded=False):

        st.markdown('<div class="download-btn-center">', unsafe_allow_html=True)
        st.download_button(
            "Download TXT",
            data=combined,
            file_name="summary.txt",
            mime="text/plain"
        )
        st.markdown('</div>', unsafe_allow_html=True)

        if PDF_AVAILABLE:
            path = tempfile.mktemp(suffix="_summary.pdf")
            doc = canvas.Canvas(path)
            text_obj = doc.beginText(40, 800)
            for line in combined.split("\n"):
                text_obj.textLine(line[:200])
            doc.drawText(text_obj)
            doc.save()
            with open(path, "rb") as f:
                st.markdown('<div class="download-btn-center">', unsafe_allow_html=True)
                st.download_button("Download PDF", data=f, file_name="summary.pdf", mime="application/pdf")
                st.markdown('</div>', unsafe_allow_html=True)
            os.remove(path)

        if DOCX_AVAILABLE:
            path = tempfile.mktemp(suffix="_summary.docx")
            doc = Document()
            for line in combined.split("\n"):
                doc.add_paragraph(line)
            doc.save(path)
            with open(path, "rb") as f:
                st.markdown('<div class="download-btn-center">', unsafe_allow_html=True)
                st.download_button(
                    "Download DOCX",
                    data=f,
                    file_name="summary.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
                st.markdown('</div>', unsafe_allow_html=True)

# End of file
