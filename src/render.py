"""Render all 1800 frames in parallel chunks -> out/chunks/*.mp4 (video only)."""
import os, sys, subprocess
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CH = os.path.join(ROOT, "out", "chunks")
CHUNK = 60

def job(ci):
    from shots import render_frame, FPS, DUR
    total = int(round(FPS * DUR))
    a, b = ci * CHUNK, min(total, (ci + 1) * CHUNK)
    path = os.path.join(CH, f"c{ci:03d}.mp4")
    if os.path.exists(path):
        return ci
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1920x1080",
           "-r", str(FPS), "-i", "-", "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
           "-c:v", "libx264", "-preset", "medium", "-crf", "13", "-g", "30", "-colorspace", "bt709",
           "-color_primaries", "bt709", "-color_trc", "bt709", "-f", "mp4", path + ".part"]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for n in range(a, b):
        p.stdin.write(render_frame(n).tobytes())
    p.stdin.close(); p.wait()
    os.rename(path + ".part", path)
    return ci

if __name__ == "__main__":
    os.makedirs(CH, exist_ok=True)
    nchunks = 1800 // CHUNK
    with Pool(4) as pool:
        for ci in pool.imap_unordered(job, range(nchunks)):
            print("chunk", ci, "done", flush=True)
    with open(os.path.join(CH, "list.txt"), "w") as f:
        for ci in range(nchunks):
            f.write(f"file 'c{ci:03d}.mp4'\n")
    print("ALL DONE")
