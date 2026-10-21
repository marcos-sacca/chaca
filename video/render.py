"""
Genera el video vertical (720x1280) "Chacarita fecha por fecha" a partir de
video/out/steps.json (ver build_data.py).

Cada paso es una pagina HTML que se captura con Chromium headless; despues ffmpeg
une las capturas en un mp4. La grilla, los colores y las tipografias replican al
milimetro el video de referencia (medidos sobre sus fotogramas), con los escudos
de video/crests/<team_id>.png (ver extract_crests.py).

Uso:  python video/build_data.py && python video/render.py
"""
import html
import json
import os
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
FRAMES = OUT / "frames"
CRESTS = HERE / "crests"
CHROME = os.environ.get("CHROME_BIN") or next(
    (str(p) for p in sorted(Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome"))), "chromium"
)

SECONDS_PER_STEP = 2.3
SECONDS_LAST_STEP = 4.5

# Columnas (px): pos | equipo | PTS | J | Gol | +/- | G | E | P | Ultimas   (suman 686 = ancho interior de la tarjeta)
COLS = "50px 237px 50px 34px 74px 34px 40px 24px 38px 105px"
ROW_H = 45.33

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:720px;height:1280px;background:#082f1f;overflow:hidden;
  font-family:'Liberation Sans',Arimo,Arial,Helvetica,sans-serif;color:#f3fff8}
.page{position:relative;width:720px;height:1280px;background:#082f1f}
.t{position:absolute;left:0;width:720px;text-align:center;white-space:nowrap}
.brand{top:10px;line-height:20px;font-size:16.5px;font-weight:700;color:#a3c1b1}
.fecha{top:36px;line-height:24px;font-size:20px;font-weight:700}
.title{top:68px;line-height:34px;font-size:25.5px;font-weight:700}
.sub{top:107px;line-height:22px;font-size:16.5px;color:#a9c4b6}
.points{top:138px;line-height:24px;font-size:19.75px;font-weight:700;color:#c8f6a6}
.card{position:absolute;left:16px;top:182px;width:688px;height:1044px;border:1.5px solid #5a7e6d;border-radius:22px;
  background:#082a1a;overflow:hidden}
.zone{height:46px;line-height:41px;padding-left:21px;font-size:25px;font-weight:700;border-bottom:1px solid #406252}
.grid{display:grid;grid-template-columns:__COLS__}
.head{height:51px;border-bottom:1px solid #456a56;align-items:center;font-size:17px;color:#a9c4b6}
.head>div,.row>div{text-align:center;height:100%;display:flex;align-items:center;justify-content:center}
.row>div{padding-bottom:5px}  /* el texto del original queda ~2.5px por encima del centro de la fila */
.head .left{justify-content:flex-start;padding-left:8px;color:#e8f5ee}
.head .b{font-weight:700;color:#f3fff8}
.sepL{border-left:1px solid #466b57}
.row{position:relative;height:__ROWH__px;font-size:18.5px;color:#b9d1c4}
.row:nth-child(odd){background:#1f4430}.row:nth-child(even){background:#133a28}
.row.mine::after{content:'';position:absolute;inset:0;border:3px solid #bdf08f;pointer-events:none}
.pos{font-weight:700;font-size:19.5px;color:#fff}
.pos.final{background:#00b6e2}.pos.po{background:#a421ed}.pos.desc{background:#ef0033}
.team{position:relative;justify-content:flex-start!important;padding-left:45px;font-size:20.5px;font-weight:700;color:#fff;white-space:nowrap}
.team img{position:absolute;left:5px;top:-1px;width:38px;height:43px}
.pts{font-weight:700;font-size:19.25px;color:#fff}
.row>div.form{justify-content:flex-start;padding:3px 0 0 3px;gap:2px}  /* los cuadraditos van ~4px mas abajo que el texto */
.form i{font-style:normal;width:18px;height:22px;border-radius:3px;font-size:18px;font-weight:700;color:#1b1b17;
  display:flex;align-items:center;justify-content:center;line-height:22px}
.form i.V{background:#84b361}.form i.E{background:#ecc73b}.form i.D{background:#ec4f63}
.legend{border-top:3px solid #84b75d}
.legend div{height:38.7px;display:flex;align-items:flex-start;padding:0 0 0 15px;gap:12px;font-size:18.5px;line-height:29px;color:#eef8f2;
  border-bottom:1px solid #3b6350}
.legend div:last-child{border-bottom:0}
.dot{width:17px;height:17px;border-radius:50%;margin-top:6px}
.bar{position:absolute;left:20px;top:1242px;width:680px;height:6px;border-radius:3px;background:#31563e}
.bar i{display:block;height:6px;border-radius:3px;background:#bcf18d}
.foot{top:1257px;line-height:18px;font-size:14.5px;color:#8fb3a2}
""".replace("__COLS__", COLS).replace("__ROWH__", str(ROW_H))


def crest(tid):
    return f'<img src="file://{CRESTS / f"{tid}.png"}">' if (CRESTS / f"{tid}.png").exists() else ""


def head_lines(step, meta, chac):
    h, a = meta[str(step["home"])]["name"], meta[str(step["away"])]["name"]
    fecha = f'FECHA {step["round"]:02d} &nbsp;·&nbsp; {step["table_date"]}'
    day = step["date"][:5]
    if step["kind"] == "pending":
        return fecha, f'{html.escape(h)} &nbsp;vs.&nbsp; {html.escape(a)}', "PARTIDO PENDIENTE AL CIERRE DE ESTA FECHA"
    title = f'{html.escape(h)} &nbsp;{step["hs"]} – {step["as_"]}&nbsp; {html.escape(a)}'
    if step["kind"] == "recovered":
        return fecha + " &nbsp;·&nbsp; RECUPERADA", title, f'{step["note"].split("· ")[-1].capitalize()} · Resultado de Chacarita'
    return fecha, title, f"{day} · Resultado de Chacarita"


def page(step, meta, chac, idx, total):
    fecha, title, sub = head_lines(step, meta, chac)
    pts = step["chac_pts"]
    rows = []
    for r in step["table"]:
        pos = r["pos"]
        pc = "final" if pos == 1 else "po" if pos <= 8 else "desc" if pos >= 17 else ""
        form = "".join(f"<i class='{x}'>{x}</i>" for x in reversed(r["form"]))  # mas reciente a la izquierda, como el original
        rows.append(
            f'<div class="row grid{" mine" if r["team"] == chac else ""}"><div class="pos {pc}">{pos}</div>'
            f'<div class="team sepL">{crest(r["team"])}{html.escape(meta[str(r["team"])]["name"])}</div>'
            f'<div class="pts sepL">{r["pts"]}</div><div class="sepL">{r["pj"]}</div><div>{r["gf"]}:{r["gc"]}</div>'
            f'<div>{r["dg"]}</div><div>{r["g"]}</div><div>{r["e"]}</div><div>{r["p"]}</div>'
            f'<div class="form">{form}</div></div>'
        )
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body><div class="page">
<div class="t brand">Chacarita Juniors · Primera Nacional 2026</div>
<div class="t fecha">{fecha}</div><div class="t title">{title}</div><div class="t sub">{sub}</div>
<div class="t points">CHACARITA: {step["chac_pos"]}.º · {pts} PUNTO{"S" if pts != 1 else ""}</div>
<div class="card"><div class="zone">ZONA B</div>
<div class="head grid"><div class="b">#</div><div class="left sepL">Equipos</div><div class="b sepL">PTS</div><div class="sepL">J</div><div>Gol</div><div>+/-</div><div>G</div><div>E</div><div>P</div><div>Últimas</div></div>
{"".join(rows)}
<div class="legend"><div><span class="dot" style="background:#0cb4e8"></span>Final</div>
<div><span class="dot" style="background:#a924ee"></span>Playoffs ascenso</div>
<div><span class="dot" style="background:#ef0033"></span>Descenso</div></div></div>
<div class="bar"><i style="width:{100*idx/total:.2f}%"></i></div>
<div class="t foot">Chacarita Juniors · Recorrido fecha por fecha</div></div></body></html>"""


def main():
    data = json.load(open(OUT / "steps.json", encoding="utf-8"))
    meta, chac, steps = data["teams"], data["chacarita"], data["steps"]
    if FRAMES.exists():
        shutil.rmtree(FRAMES)
    FRAMES.mkdir(parents=True)
    for i, s in enumerate(steps, 1):
        f = FRAMES / f"{i:03d}.html"
        f.write_text(page(s, meta, chac, i, len(steps)), encoding="utf-8")
        subprocess.run(
            [CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files",
             "--force-device-scale-factor=1", "--window-size=720,1400", f"--screenshot={f.with_suffix('.png')}", f"file://{f}"],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60,
        )
    lst = FRAMES / "list.txt"
    with open(lst, "w") as fh:
        for i in range(1, len(steps) + 1):
            d = SECONDS_LAST_STEP if i == len(steps) else SECONDS_PER_STEP
            fh.write(f"file '{i:03d}.png'\nduration {d}\n")
        fh.write(f"file '{len(steps):03d}.png'\n")
    mp4 = OUT / "chacarita_fecha_por_fecha.mp4"
    # la ventana de captura es mas alta que el viewport; el contenido ocupa los primeros 1280 px
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-vf", "crop=720:1280:0:0,fps=20,format=yuv420p",
         "-c:v", "libx264", "-crf", "18", "-movflags", "+faststart", str(mp4)], check=True)
    print(f"{len(steps)} pantallas -> {mp4} ({mp4.stat().st_size/1e6:.1f} MB)")


if __name__ == "__main__":
    main()
