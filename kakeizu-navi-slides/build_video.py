# -*- coding: utf-8 -*-
"""スライドHTML→PNG、edge-ttsでナレーション、ffmpegでMP4結合。"""
import asyncio, base64, os, subprocess, sys, json
from pathlib import Path
import imageio_ffmpeg
from slides import SLIDES

ROOT = Path(__file__).parent
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
VOICE = "ja-JP-NanamiNeural"   # 女性・自然な日本語
RATE = "+6%"                    # 少し速め

# icon を base64 data URI 化（file://依存を避ける）
icon_b64 = base64.b64encode((ROOT / "icon.png").read_bytes()).decode()
icon_uri = f"data:image/png;base64,{icon_b64}"
CSS = (ROOT / "style.css").read_text(encoding="utf-8")


def page_html(body):
    body = body.replace('src="icon.png"', f'src="{icon_uri}"')
    return f"<!DOCTYPE html><html lang='ja'><head><meta charset='utf-8'><style>{CSS}</style></head><body>{body}</body></html>"


async def render_images():
    from playwright.async_api import async_playwright
    out = []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=2)
        for i, (body, _) in enumerate(SLIDES, 1):
            await page.set_content(page_html(body), wait_until="networkidle")
            await page.wait_for_timeout(350)
            fn = ROOT / f"img_{i:02d}.png"
            await page.screenshot(path=str(fn), clip={"x": 0, "y": 0, "width": 1280, "height": 720})
            out.append(fn)
            print(f"  IMG slide {i}")
        await browser.close()
    return out


async def render_audio():
    import edge_tts
    durations = []
    for i, (_, narration) in enumerate(SLIDES, 1):
        mp3 = ROOT / f"aud_{i:02d}.mp3"
        com = edge_tts.Communicate(narration, VOICE, rate=RATE)
        await com.save(str(mp3))
        # 長さ取得
        dur = ffprobe_duration(mp3)
        durations.append(dur)
        print(f"  TTS slide {i}: {dur:.1f}s")
    return durations


def ffprobe_duration(mp3):
    # ffmpegで長さを測る（ffprobe無しでもstderr解析）
    r = subprocess.run([FFMPEG, "-i", str(mp3)], capture_output=True, text=True)
    for line in r.stderr.splitlines():
        if "Duration:" in line:
            t = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = t.split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    return 4.0


def build_segments(durations):
    """各スライドを 画像+音声(+末尾0.6s余白) の個別mp4にする。"""
    seg_files = []
    pad = 0.7
    for i in range(1, len(SLIDES) + 1):
        img = ROOT / f"img_{i:02d}.png"
        aud = ROOT / f"aud_{i:02d}.mp3"
        seg = ROOT / f"seg_{i:02d}.mp4"
        dur = durations[i - 1] + pad
        cmd = [
            FFMPEG, "-y",
            "-loop", "1", "-i", str(img),
            "-i", str(aud),
            "-f", "lavfi", "-t", f"{dur:.2f}", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-filter_complex", "[1:a][2:a]amix=inputs=2:duration=longest:dropout_transition=0[a]",
            "-map", "0:v", "-map", "[a]",
            "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-t", f"{dur:.2f}", "-r", "30",
            str(seg),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        seg_files.append(seg)
        print(f"  SEG slide {i}: {dur:.1f}s")
    return seg_files


def concat(seg_files, out):
    lst = ROOT / "concat.txt"
    lst.write_text("".join(f"file '{s.as_posix()}'\n" for s in seg_files), encoding="utf-8")
    cmd = [FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-r", "30", str(out)]
    subprocess.run(cmd, check=True, capture_output=True)


async def main():
    print("[1/4] スライド画像をレンダリング...")
    await render_images()
    print("[2/4] ナレーション音声を生成...")
    durations = await render_audio()
    print("[3/4] スライドごとの動画セグメントを作成...")
    segs = build_segments(durations)
    print("[4/4] 結合してMP4を書き出し...")
    out = ROOT / "kakeizu-navi-intro.mp4"
    concat(segs, out)
    total = sum(durations) + 0.7 * len(durations)
    print(f"\n完成: {out}")
    print(f"合計尺: 約 {int(total // 60)}分{int(total % 60)}秒")
    print(f"サイズ: {out.stat().st_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    asyncio.run(main())
