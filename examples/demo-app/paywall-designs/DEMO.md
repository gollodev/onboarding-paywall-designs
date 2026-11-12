# Demo: Brotia (app ficticia)

Este ejemplo muestra la skill de principio a fin sobre un proyecto Expo ficticio (`examples/demo-app/`).
**Todo es inventado para la demo**: la app, los precios ($4.99/mes, $29.99/año, prueba de 7 días) y las respuestas de la Fase 2.
En un proyecto real, esos datos los da el usuario y nunca se inventan.

| Fase | Archivo |
|------|---------|
| 1. Descubrimiento | `project-brief.auto.md` (salida bruta del script), `discovery.json`, `brand.json` → `project-brief.md` (revisado por el agente) |
| 2. Preguntas | Respuestas simuladas, resumidas en `project-brief.md` §7 |
| 3. Estrategia | `conversion-strategy.md` |
| 4. Config | `config.json` |
| 5. Render + chequeos | `output/<device>/<theme>/*.png` (52 PNG), `output/quality-report.md` |
| 6. Entrega | `output/contact-sheet.png`, `output/contact-sheet.pdf`, `pending.md` |

Pendientes que se dejaron a propósito para mostrar el comportamiento: no hay prueba social real (aparece un marcador visible en `12-paywall-benefits`) y faltan las URLs legales.

Versión en inglés: `../paywall-designs-en/` (mismo proyecto y pantallas; solo cambian `locale` y los textos de `config.json`).
