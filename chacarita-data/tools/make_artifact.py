"""Arma una sola página HTML autosuficiente (JS, CSS, datos, fuentes e imágenes embebidos) para publicarla como Artifact de claude.ai.

Uso:  python3 -I tools/make_artifact.py <esbuild> <salida.html>
(<esbuild> es la ruta al binario de esbuild). El sitio normal no la necesita: se publica tal cual como carpeta estática.
"""
import base64, json, pathlib, re, subprocess, sys

root = pathlib.Path(__file__).resolve().parent.parent
esbuild, out = sys.argv[1], pathlib.Path(sys.argv[2])

js = subprocess.run([esbuild, str(root / "js/app.js"), "--bundle", "--format=iife", "--minify", "--target=es2020"], capture_output=True, text=True, check=True).stdout

# imágenes: se referencian por nombre y salen de un mapa de data: URIs
imgs = {}
for f in sorted((root / "assets/img").iterdir()):
    if f.suffix in (".jpg", ".png", ".svg"):
        mime = {".jpg": "image/jpeg", ".png": "image/png", ".svg": "image/svg+xml"}[f.suffix]
        imgs[f.name] = f"data:{mime};base64," + base64.b64encode(f.read_bytes()).decode()
js = re.sub(r"""(["'])assets/img/([\w.-]+\.(?:jpg|png|svg))\1""", lambda m: f'window.__IMG["{m.group(2)}"]', js)

# datos: reemplazan a fetch() de los JSON
emb = {}
for f in (root / "data").glob("*.json"):
    emb[f"data/{f.name}"] = json.loads(f.read_text(encoding="utf-8"))
emb["data/enrichment/parche_partidos.json"] = json.loads((root / "data/enrichment/parche_partidos.json").read_text(encoding="utf-8"))
emb["assets/img/credits.json"] = json.loads((root / "assets/img/credits.json").read_text(encoding="utf-8"))
emb_json = json.dumps(emb, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

# CSS con las fuentes embebidas
css = (root / "css/main.css").read_text(encoding="utf-8")
fonts = ""
for fam, fname, extra in (("Archivo", "Archivo-wdth-latin.woff2", "font-stretch: 62% 125%;"), ("Inter", "Inter-latin.woff2", "")):
    b = base64.b64encode((root / "assets/fonts" / fname).read_bytes()).decode()
    fonts += f'@font-face {{ font-family: "{fam}"; font-style: normal; font-display: swap; font-weight: 100 900; {extra} src: url(data:font/woff2;base64,{b}) format("woff2"); }}\n'

# cuerpo de index.html (sin <head>)
html = (root / "index.html").read_text(encoding="utf-8")
body = re.search(r"<body>(.*)</body>", html, re.S).group(1)
body = re.sub(r"<script type=\"module\".*?</script>", "", body)
body = re.sub(r"<noscript>.*?</noscript>", "", body, flags=re.S)
body = re.sub(r'<img src="assets/img/([\w.-]+)"', r'<img data-img="\1"', body)

shim = """window.__EMBEDDED__=true;window.__IMG=JSON.parse(document.getElementById('imgs').textContent);
(function(){var E=JSON.parse(document.getElementById('emb').textContent),f=window.fetch;
window.fetch=function(u,o){var k=String(u);if(Object.prototype.hasOwnProperty.call(E,k))return Promise.resolve(new Response(JSON.stringify(E[k]),{headers:{'content-type':'application/json'}}));return f.call(this,u,o)};
document.querySelectorAll('img[data-img]').forEach(function(i){i.src=window.__IMG[i.dataset.img]});})();"""

page = f"""<title>chacarita-data</title>
<style>
{fonts}{css}
</style>
{body}
<script type="application/json" id="imgs">{json.dumps(imgs, separators=(",", ":"))}</script>
<script type="application/json" id="emb">{emb_json}</script>
<script>{shim}</script>
<script>{js.replace("</script", "<\\/script")}</script>
"""
out.write_text(page, encoding="utf-8")
print(out, round(out.stat().st_size / 1e6, 2), "MB")
