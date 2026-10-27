Vas a trabajar en el sitio "chacarita-data" (datos de Chacarita Juniors). Ejecutá todo lo de abajo de corrido, sin pedirme confirmación, respetando las reglas. Respondeme en español.

PARTE 1 — PREPARAR EL CÓDIGO (PowerShell de Windows, un comando por línea, sin `&&`)
Estás en una carpeta de mi PC llamada chaca_2 (o similar). El código está en el repo https://github.com/marcos-sacca/chaca, rama `claude/eager-dirac-icc7t3`, dentro de la subcarpeta `chacarita-data/`.
1. Corré `git status` y `git remote -v`.
2. Si la carpeta es el repo marcos-sacca/chaca Y `git status` está limpio (sin cambios ni archivos sin seguimiento): corré `git fetch origin`, `git checkout claude/eager-dirac-icc7t3` y `git checkout -b diseno-local`. Trabajá ahí.
3. Si NO es el repo, o tiene cambios sin guardar: NO toques esa carpeta (no hagas stash, reset, checkout ni borrados). Clonalo en una carpeta hermana: `git clone --branch claude/eager-dirac-icc7t3 https://github.com/marcos-sacca/chaca.git chaca_web` y después `git checkout -b diseno-local` ahí. Trabajá en chaca_web y avisame al final.
4. Verificá que existan `chacarita-data/index.html`, `css`, `js`, `data` y `assets`. Leé `chacarita-data/README.md`.

PARTE 2 — VER EL SITIO
Es un sitio estático (HTML, CSS y módulos ES, sin build). Levantalo con `npx --yes serve chacarita-data -l 8000` (en segundo plano) y abrilo con Playwright en http://localhost:8000. Recorré en escritorio (1360 px) y en celular (390 px): inicio, rivales y la ficha de un rival (#/rivales/Boca%20Juniors), partidos y la ficha de un partido (#/partido/242), jugadores y un perfil (#/jugadores/Francisco%20Campana), temporadas y una temporada (#/temporadas/1969), récords (las 4 pestañas: rachas, marcas, temporadas, canchas; usá #/records?s=curiosidades etc.), efemérides y datos (#/datos). Sacá capturas de pantalla completas y guardalas en una carpeta `capturas/antes` fuera de `chacarita-data/` (por ejemplo ../capturas/antes).

PARTE 3 — MEJORAR EL DISEÑO
Objetivo: moderno pero que NO parezca generado por IA, lo más amigable posible para el usuario, sin modo oscuro y sin subtítulos innecesarios. Base blanca/gris con el rojo y negro de Chacarita, animaciones cuidadas, y con el escudo, la camiseta y la cancha presentes. La tipografía actual es Archivo + Inter (no me gustaba la anterior ni el color crema). Hacé, en orden:
1. Auditoría de diseño con Impeccable (crítica y lista de problemas concretos).
2. Pasada con emil-design-eng sobre animaciones y detalles de interacción.
3. Pasada con break-ui usando datos extremos: nombres larguísimos, partidos sin goleadores ni formación, rivales con un solo partido, temporadas sin posición, filtros que no devuelven nada.
4. Corregí lo que encuentres con cambios chicos y revisables. Si alguna skill no está disponible en esta sesión (por ejemplo porque VS Code no se reinició), hacé esa pasada a mano con el mismo criterio y avisame cuál fue.
5. Sacá capturas de los mismos recorridos en `capturas/despues`.
6. Revisá que no haya errores en la consola del navegador en ninguna pantalla y que no haya scroll horizontal en 390 px.

REGLAS
- No modifiques `chacarita-data/data/` ni `chacarita-data/tools/`: son datos verificados contra mi Excel. No inventes datos, nombres, fotos ni textos sobre la historia del club.
- Mantené los créditos de las fotos (assets/img/credits.json) y el texto «agregado» en los datos completados.
- Commits chicos y claros en la rama `diseno-local`. NO hagas push ni crees pull requests. No instales paquetes globales nuevos ni cambies mi configuración de Claude Code.
- Si algo falla, no improvises con alternativas riesgosas: copiá el error y qué probaste.

INFORME FINAL
Resumen corto con: en qué carpeta y rama quedó el trabajo, la lista de problemas encontrados y cuáles corregiste, qué quedó pendiente o necesita mi decisión, dónde están las capturas antes y después, y cómo ver el sitio (el comando del servidor y la dirección).
