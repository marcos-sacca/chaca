"""Arma una sola página HTML autosuficiente (JS, CSS, datos e imágenes embebidos) para publicarla como Artifact.

Uso:  python3 -I tools/make_artifact.py <esbuild> <salida.html>
Tipografías (Archivo e Inter, licencia OFL), CSS, datos e imágenes van dentro del archivo.
"""
import base64, json, pathlib, re, subprocess, sys

root = pathlib.Path(__file__).resolve().parent.parent
esbuild, out = sys.argv[1], pathlib.Path(sys.argv[2])
js = subprocess.run([esbuild, str(root / "js/app.js"), "--bundle", "--format=iife", "--minify", "--target=es2020"], capture_output=True, text=True, check=True).stdout
imgs = {}
for f in sorted((root / "assets/img").rglob("*")):
    if f.suffix in (".jpg", ".png", ".svg"):
        mime = {".jpg": "image/jpeg", ".png": "image/png", ".svg": "image/svg+xml"}[f.suffix]
        imgs[f.relative_to(root).as_posix()] = f"data:{mime};base64," + base64.b64encode(f.read_bytes()).decode()
emb = {f"data/{f.name[:-5]}.json": json.loads(f.read_text(encoding="utf-8")) for f in (root / "data").glob("*.json")}
emb_json = json.dumps(emb, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
css = (root / "css/main.css").read_text(encoding="utf-8")
fonts = ""
for fam, fname, extra in (("Archivo", "Archivo-wdth-latin.woff2", "font-stretch: 62% 125%;"), ("Inter", "Inter-latin.woff2", "")):
    b = base64.b64encode((root / "assets/fonts" / fname).read_bytes()).decode()
    fonts += f'@font-face {{ font-family: "{fam}"; font-style: normal; font-display: swap; font-weight: 100 900; {extra} src: url(data:font/woff2;base64,{b}) format("woff2"); }}\n'
html = (root / "index.html").read_text(encoding="utf-8")
body = re.search(r"<body>(.*)</body>", html, re.S).group(1)
body = re.sub(r"<script type=\"module\".*?</script>", "", body)
body = re.sub(r"<noscript>.*?</noscript>", "", body, flags=re.S)
shim = """window.__EMBEDDED__=true;window.__IMG=JSON.parse(document.getElementById('imgs').textContent);
(function(){var E=JSON.parse(document.getElementById('emb').textContent),f=window.fetch;
window.fetch=function(u,o){var k=String(u);if(Object.prototype.hasOwnProperty.call(E,k))return Promise.resolve(new Response(JSON.stringify(E[k]),{headers:{'content-type':'application/json'}}));return f.call(this,u,o)};})();"""
page = f"""<title>B Nacional Histórica</title>
<meta name="claude:viewport-fit-sides" content="cover">
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
print(out, round(out.stat().st_size / 1e6, 2), "MB", len(imgs), "imágenes")
