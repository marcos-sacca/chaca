"""
Actualiza la cache de Sofascore con las fechas de la Primera Nacional 2026 que
todavia no estaban jugadas cuando se bajo (scripts/fetch_zone_b.py, 6-sep-2026).

Vuelve a pedir SOLO las fechas que tienen partidos sin terminar; el resto se
queda como esta. Despues correr build_data.py y render.py.

Necesita: curl_cffi (ver scripts/sofa_lib.py) y acceso a api.sofascore.com
(el entorno cloud lo bloquea; correrlo en la PC o habilitando el dominio).
Hace pocos requests (hasta 36, con la pausa de cortesia de sofa_lib).

Uso:  python video/refresh_data.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import sofa_lib as sl  # noqa: E402

TOURNAMENT_ID, SEASON_ID, TOTAL_ROUNDS = 703, 87940, 36


def main():
    stale = []
    for r in range(1, TOTAL_ROUNDS + 1):
        endpoint = f"/unique-tournament/{TOURNAMENT_ID}/season/{SEASON_ID}/events/round/{r}"
        cached = sl._cache_path(endpoint)
        if cached.exists():
            evs = json.load(open(cached, encoding="utf-8")).get("events", [])
            if evs and all(e["status"]["type"] in ("finished", "canceled") for e in evs):
                continue
        stale.append((r, endpoint))
    print(f"{len(stale)} fechas por actualizar: {[r for r, _ in stale]}")
    for r, endpoint in stale:
        data = sl.get(endpoint, use_cache=False) or {}
        n_ended = sum(e["status"]["type"] == "finished" for e in data.get("events", []))
        print(f"  fecha {r}: {n_ended}/{len(data.get('events', []))} partidos terminados")
    print("Listo. Ahora: python video/build_data.py && python video/render.py")


if __name__ == "__main__":
    main()
