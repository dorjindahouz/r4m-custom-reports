"""Stream the 1.25 GB CONTOUR.DXF into a light raster backdrop for the mine map.

The DXF is ASCII with 3D POLYLINE/VERTEX entities whose vertices are ~0.1-0.5 m
apart, so plotting the vertex POINTS at ~1.25 m/px already draws continuous
contour curves - no segment rasterization needed. Vertices are streamed in
group-code/value pairs and binned into a 2D histogram; mean elevation per pixel
drives a subtle hypsometric tint.

Run:  python prepare_contour.py
Out:  data/contour_bg.png  (RGBA, transparent background)
      data/contour_bg.json (world bounds of the image, UTM)
"""
import json
import os
import time

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
DXF = os.path.join(os.path.dirname(HERE), "CONTOUR.DXF")
OUT_PNG = os.path.join(HERE, "data", "contour_bg.png")
OUT_JSON = os.path.join(HERE, "data", "contour_bg.json")

# Fixed world window (UTM) around the pit - clip everything else.
X0, X1 = 482_300.0, 485_500.0
Y0, Y1 = 4_859_400.0, 4_863_600.0
MPP = 1.4                      # metres per pixel
W = int((X1 - X0) / MPP)       # ~2285
H = int((Y1 - Y0) / MPP)       # ~3000
BATCH = 2_000_000


def main():
    t0 = time.time()
    cnt = np.zeros((H, W), dtype=np.uint16)
    zsum = np.zeros((H, W), dtype=np.float32)
    xs, ys, zs = [], [], []
    n_vert = 0

    def flush():
        nonlocal xs, ys, zs
        if not xs:
            return
        ax = np.asarray(xs, dtype=np.float64)
        ay = np.asarray(ys, dtype=np.float64)
        az = np.asarray(zs, dtype=np.float32)
        m = (ax >= X0) & (ax < X1) & (ay >= Y0) & (ay < Y1)
        px = ((ax[m] - X0) / MPP).astype(np.int32)
        py = ((Y1 - ay[m]) / MPP).astype(np.int32)   # north-up image
        np.add.at(cnt, (py, px), 1)
        np.add.at(zsum, (py, px), az[m])
        xs, ys, zs = [], [], []

    with open(DXF, "r", encoding="ascii", errors="ignore") as f:
        x = y = z = None
        while True:
            code = f.readline()
            if not code:
                break
            val = f.readline()
            c = code.strip()
            if c == "10":
                x = float(val)
            elif c == "20":
                y = float(val)
            elif c == "30":
                z = float(val)
                if x is not None and y is not None:
                    xs.append(x); ys.append(y); zs.append(z)
                    n_vert += 1
                    if len(xs) >= BATCH:
                        flush()
                        print(f"  {n_vert/1e6:.0f}M vertices, {time.time()-t0:.0f}s")
                x = y = None
    flush()

    hit = cnt > 0
    zmean = np.where(hit, zsum / np.maximum(cnt, 1), np.nan)
    zlo, zhi = np.nanpercentile(zmean[hit], [2, 98])
    print(f"vertices: {n_vert:,}  lit pixels: {hit.sum():,}  z range {zlo:.0f}-{zhi:.0f} m")

    # hypsometric tint: low = muted sage, high = muted tan; alpha on lines only
    tnorm = np.clip((zmean - zlo) / max(zhi - zlo, 1), 0, 1)
    lo = np.array([148, 168, 154], dtype=np.float32)   # sage
    hi = np.array([196, 176, 148], dtype=np.float32)   # tan
    rgb = (lo[None, None, :] * (1 - tnorm[..., None]) +
           hi[None, None, :] * tnorm[..., None])
    img = np.zeros((H, W, 4), dtype=np.uint8)
    img[..., :3] = np.nan_to_num(rgb).astype(np.uint8)
    img[..., 3] = np.where(hit, 175, 0).astype(np.uint8)

    os.makedirs(os.path.dirname(OUT_PNG), exist_ok=True)
    Image.fromarray(img, "RGBA").save(OUT_PNG, optimize=True)
    with open(OUT_JSON, "w") as fh:
        json.dump({"x0": X0, "x1": X1, "y0": Y0, "y1": Y1,
                   "width": W, "height": H, "mpp": MPP,
                   "zlo": float(zlo), "zhi": float(zhi)}, fh)
    print(f"wrote {OUT_PNG} ({os.path.getsize(OUT_PNG)/1024:.0f} KB), "
          f"{OUT_JSON}  in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
