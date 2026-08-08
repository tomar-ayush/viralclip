"""
ViralClip FFmpeg Render Service
================================
Standalone FastAPI microservice that replaces Remotion Lambda.
Composes 9:16 short-form videos using pure ffmpeg:
  - Background video/image (looped)
  - Voiceover audio overlay
  - Word-level burned-in captions (ASS format)
  - Final MP4 upload to IDrive E2

Deploy to: HuggingFace Spaces (Docker), Render.com, or Koyeb
No credit card required on any of these platforms.
"""

import asyncio
import json
import os
import subprocess
import tempfile
import uuid

import boto3
import httpx
from botocore.config import Config
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="ViralClip FFmpeg Render Service")

# ── Config from environment ────────────────────────────────────────────────
E2_ENDPOINT   = os.environ.get("E2_ENDPOINT_URL", "https://s3.ap-northeast-1.idrivee2.com")
E2_REGION     = os.environ.get("E2_REGION", "ap-northeast-1")
E2_KEY_ID     = os.environ.get("E2_ACCESS_KEY_ID", "")
E2_SECRET     = os.environ.get("E2_SECRET_ACCESS_KEY", "")
E2_BUCKET     = os.environ.get("E2_BUCKET_NAME", "viralclip")
E2_DOMAIN     = os.environ.get("E2_PUBLIC_DOMAIN", "").rstrip("/")
RENDER_SECRET = os.environ.get("RENDER_SECRET", "changeme")  # Simple auth token

# Video output specs (9:16 vertical short-form)
OUTPUT_WIDTH  = 1080
OUTPUT_HEIGHT = 1920
OUTPUT_FPS    = 30


# ── Request / Response schemas ─────────────────────────────────────────────

class WordCaption(BaseModel):
    word: str
    start: float  # seconds
    end: float    # seconds


class RenderRequest(BaseModel):
    job_id: str
    audio_url: str              # public URL to mp3 voiceover
    background_asset_id: str   # public URL or IDrive E2 key for bg video/image
    word_captions: list[WordCaption]
    secret: str                 # simple auth


class RenderResponse(BaseModel):
    render_id: str
    output_url: str
    duration_seconds: float


# ── Storage helper ─────────────────────────────────────────────────────────

def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=E2_ENDPOINT,
        aws_access_key_id=E2_KEY_ID,
        aws_secret_access_key=E2_SECRET,
        region_name=E2_REGION,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        ),
    )


def upload_to_e2(local_path: str, e2_key: str) -> str:
    """Upload a local file to IDrive E2. Returns public URL."""
    client = get_s3_client()
    with open(local_path, "rb") as f:
        client.put_object(
            Bucket=E2_BUCKET,
            Key=e2_key,
            Body=f,
            ContentType="video/mp4",
        )
    return f"{E2_DOMAIN}/{e2_key}"


# ── Caption builder ────────────────────────────────────────────────────────

def build_ass_subtitles(captions: list[WordCaption]) -> str:
    """
    Build ASS subtitle file with viral-style formatting:
    - Large bold white text with thick black outline
    - Centered at bottom third of frame (9:16)
    - 3-word chunks for readability
    """
    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "PlayResX: 1080\n"
        "PlayResY: 1920\n"
        "ScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        # White text, black outline, bold, size 90, bottom-center (Alignment=2)
        "Style: Default,Arial,90,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,"
        "-1,0,0,0,100,100,0,0,1,6,2,2,50,50,300,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )

    events = []
    chunk_size = 3
    chunks = [captions[i:i+chunk_size] for i in range(0, len(captions), chunk_size)]

    def fmt_ass(sec: float) -> str:
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        s = sec % 60
        return f"{h}:{m:02d}:{s:05.2f}"

    for chunk in chunks:
        start = chunk[0].start
        end = chunk[-1].end
        # All caps for viral style, words joined
        text = " ".join(w.word for w in chunk).upper()
        events.append(
            f"Dialogue: 0,{fmt_ass(start)},{fmt_ass(end)},Default,,0,0,0,,{text}"
        )

    return header + "\n".join(events)


# ── File downloader ────────────────────────────────────────────────────────

async def download_file(url: str, dest: str):
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
        with open(dest, "wb") as f:
            f.write(response.content)


def run_ffmpeg(cmd: list[str]):
    """Run an ffmpeg command, raise RuntimeError on failure."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg error:\n{result.stderr[-2000:]}")
    return result


# ── Core render pipeline ───────────────────────────────────────────────────

async def compose_video(
    job_id: str,
    audio_url: str,
    background_url: str,
    captions: list[WordCaption],
    workdir: str,
) -> tuple[str, float]:
    """
    Full ffmpeg pipeline:
      1. Download background asset + audio in parallel
      2. Scale/pad background to 9:16 (1080x1920)
      3. Loop background video to match audio length
      4. Burn in ASS captions (hardcoded for all platforms)
      5. Mix voiceover audio
      6. Output web-optimized MP4

    Returns: (output_path, duration_seconds)
    """
    bg_raw_path  = os.path.join(workdir, "bg_raw")
    audio_path   = os.path.join(workdir, "audio.mp3")
    subs_path    = os.path.join(workdir, "captions.ass")
    looped_path  = os.path.join(workdir, "bg_looped.mp4")
    output_path  = os.path.join(workdir, "output.mp4")

    # ── Step 1: Download background + audio in parallel
    await asyncio.gather(
        download_file(background_url, bg_raw_path),
        download_file(audio_url, audio_path),
    )

    # ── Step 2: Write ASS caption file
    ass_content = build_ass_subtitles(captions)
    with open(subs_path, "w", encoding="utf-8") as f:
        f.write(ass_content)

    # ── Step 3: Get audio duration via ffprobe
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "json", audio_path],
        capture_output=True, text=True,
    )
    audio_duration = float(json.loads(probe.stdout)["format"]["duration"])

    # ── Step 4: Detect image vs video background
    is_image = background_url.lower().rsplit("?", 1)[0].endswith(
        (".jpg", ".jpeg", ".png", ".webp", ".gif")
    )

    if is_image:
        # Still image → loop as video for the full audio duration
        run_ffmpeg([
            "ffmpeg", "-y",
            "-loop", "1", "-i", bg_raw_path,
            "-t", str(audio_duration),
            "-vf", (
                f"scale={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:"
                "force_original_aspect_ratio=increase,"
                f"crop={OUTPUT_WIDTH}:{OUTPUT_HEIGHT},"
                f"fps={OUTPUT_FPS}"
            ),
            "-c:v", "libx264", "-preset", "fast",
            "-pix_fmt", "yuv420p",
            looped_path,
        ])
    else:
        # Video → loop to fill audio duration, strip original audio
        run_ffmpeg([
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", bg_raw_path,
            "-t", str(audio_duration),
            "-vf", (
                f"scale={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:"
                "force_original_aspect_ratio=increase,"
                f"crop={OUTPUT_WIDTH}:{OUTPUT_HEIGHT},"
                f"fps={OUTPUT_FPS}"
            ),
            "-c:v", "libx264", "-preset", "fast",
            "-an", "-pix_fmt", "yuv420p",
            looped_path,
        ])

    # ── Step 5: Burn captions + mix audio → final MP4
    # Escape path for ASS filter (Windows backslashes need escaping)
    safe_subs = subs_path.replace("\\", "/").replace(":", "\\:")
    run_ffmpeg([
        "ffmpeg", "-y",
        "-i", looped_path,
        "-i", audio_path,
        "-vf", f"ass={safe_subs}",       # hardcode captions into video frames
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",                     # 18=lossless quality, 28=small file
        "-c:a", "aac", "-b:a", "192k",
        "-ar", "44100",
        "-shortest",                      # trim to shortest stream
        "-movflags", "+faststart",        # web-optimized: moov atom at start
        "-pix_fmt", "yuv420p",
        output_path,
    ])

    return output_path, audio_duration


# ── API Endpoints ──────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Health check — verifies ffmpeg is installed."""
    result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
    return {
        "status": "ok" if result.returncode == 0 else "ffmpeg_missing",
        "ffmpeg_available": result.returncode == 0,
    }


@app.post("/render", response_model=RenderResponse)
async def render_video(req: RenderRequest):
    """
    Main render endpoint — called by ViralClip FastAPI backend.
    Replaces the Remotion Lambda / Modal call in RemotionService.
    """
    if req.secret != RENDER_SECRET:
        raise HTTPException(status_code=401, detail="Invalid render secret")

    render_id = f"ffmpeg_{req.job_id[:8]}_{uuid.uuid4().hex[:6]}"

    with tempfile.TemporaryDirectory() as workdir:
        # Resolve background URL (key → full URL if needed)
        bg_url = req.background_asset_id
        if not bg_url.startswith("http"):
            bg_url = f"{E2_DOMAIN}/{req.background_asset_id}"

        output_path, duration = await compose_video(
            job_id=req.job_id,
            audio_url=req.audio_url,
            background_url=bg_url,
            captions=req.word_captions,
            workdir=workdir,
        )

        # Upload to IDrive E2
        e2_key = f"renders/{req.job_id}.mp4"
        output_url = upload_to_e2(output_path, e2_key)

    return RenderResponse(
        render_id=render_id,
        output_url=output_url,
        duration_seconds=round(duration, 2),
    )


if __name__ == "__main__":
    import uvicorn
    # Port 7860 = HuggingFace Spaces default
    uvicorn.run(app, host="0.0.0.0", port=7860)
