import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))
from shots import *
from PIL import Image, ImageDraw
out = sys.argv[1]
times = [float(x) for x in sys.argv[2].split(",")]
tiles = []
for t in times:
    t0 = time.time()
    im = render_frame(round(t * FPS))
    print(t, round(time.time() - t0, 2), "s", flush=True)
    tiles.append(im)
cols = 3
rows = (len(tiles) + cols - 1) // cols
sheet = Image.new("RGB", (cols * 640, rows * 360), (30, 30, 30))
for i, im in enumerate(tiles):
    sheet.paste(im.resize((640, 360), Image.LANCZOS), ((i % cols) * 640, (i // cols) * 360))
sheet.save(out)
