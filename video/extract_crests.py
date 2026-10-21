"""
Saca los escudos de la Zona B de un video de referencia (el recorrido fecha por
fecha de otro equipo, que muestra la misma tabla) y los guarda como PNG con fondo
transparente en video/crests/<team_id>.png, listos para render.py.

Sofascore sirve los escudos desde api.sofascore.app, que el entorno cloud bloquea;
el video de referencia los trae a 720x1280, la misma resolucion a la que se
vuelven a mostrar, asi que no se pierde nitidez.

Uso:  python video/extract_crests.py <video.mp4> [segundo_de_la_fecha_1]
Si en algun momento se pueden bajar los escudos originales, alcanza con pisar los
PNG de video/crests/ (render.py usa lo que haya ahi).
"""
import json
import subprocess
import sys
import tempfile
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
OUT = HERE / "crests"

# Orden de la tabla de la fecha 1 en el video de referencia (de arriba hacia abajo)
ROW_ORDER = [
    "Agropecuario", "Gimnasia y Tiro", "Gimnasia (J)", "Chicago", "Atlanta", "Chacarita",
    "San Martín", "Almagro", "Atlético Rafaela", "Patronato", "San Martín (T)", "Temperley",
    "Tristán Suárez", "Midland", "Colegiales", "Maipú", "Quilmes", "Güemes",
]
FIRST_ROW_Y, ROW_PITCH = 300.5, 45.32
BOX_X0, BOX_W = 72, 38
TOP, BOT = 21, 22          # recorte: de cy-21 a cy+22 (43 px). El escudo queda ~2px por debajo del centro de la fila
HIGHLIGHT_ROW = ROW_ORDER.index("Chicago")  # la fila resaltada del video trae un borde verde que hay que dejar afuera


def to_alpha(img, tol=26, soft=46):
    a = np.asarray(img.convert("RGB"), dtype=np.int32)
    h, w, _ = a.shape
    bg = np.median(np.concatenate([a[:, 0], a[:, -1]]), axis=0)  # solo los costados: arriba/abajo puede haber borde de la fila resaltada
    dist = np.sqrt(((a - bg) ** 2).sum(axis=2))
    bgmask = np.zeros((h, w), bool)
    q = deque()
    for x in range(w):
        for y in (0, h - 1):
            if dist[y, x] <= tol:
                bgmask[y, x] = True
                q.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if dist[y, x] <= tol and not bgmask[y, x]:
                bgmask[y, x] = True
                q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not bgmask[ny, nx] and dist[ny, nx] <= tol:
                bgmask[ny, nx] = True
                q.append((ny, nx))
    alpha = np.full((h, w), 255, np.float32)
    alpha[bgmask] = 0
    # borde suave: pixeles pegados al fondo que apenas se distinguen de el
    near = np.zeros_like(bgmask)
    near[1:] |= bgmask[:-1]; near[:-1] |= bgmask[1:]; near[:, 1:] |= bgmask[:, :-1]; near[:, :-1] |= bgmask[:, 1:]
    edge = near & ~bgmask
    alpha[edge] = np.clip((dist[edge] - tol) / (soft - tol), 0, 1) * 255
    rgba = np.dstack([a.clip(0, 255).astype(np.uint8), alpha.astype(np.uint8)])
    return Image.fromarray(rgba, "RGBA")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    video, ts = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "1")
    ids = {v["name"]: int(k) for k, v in json.load(open(HERE / "out" / "steps.json", encoding="utf-8"))["teams"].items()}
    with tempfile.TemporaryDirectory() as td:
        frame = Path(td) / "f.png"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", ts, "-i", video, "-frames:v", "1", str(frame)], check=True)
        im = Image.open(frame).convert("RGB")
    OUT.mkdir(exist_ok=True)
    for i, name in enumerate(ROW_ORDER):
        cy = round(FIRST_ROW_Y + i * ROW_PITCH)
        crop = im.crop((BOX_X0, cy - TOP, BOX_X0 + BOX_W, cy + BOT))
        out = to_alpha(crop)
        if i == 0:  # la 1.ª fila toca la linea de cabecera de la tabla
            a = np.array(out)
            a[: TOP - 16, :, 3] = 0
            out = Image.fromarray(a, "RGBA")
        if i == HIGHLIGHT_ROW:
            a = np.array(out)
            a[: TOP - 15, :, 3] = 0   # deja afuera el borde verde (cy-22..cy-19 y cy+20 en adelante)
            a[TOP + 19 :, :, 3] = 0
            out = Image.fromarray(a, "RGBA")
        out.save(OUT / f"{ids[name]}.png")
        print(f"{ids[name]:>7}  {name}")


if __name__ == "__main__":
    main()
