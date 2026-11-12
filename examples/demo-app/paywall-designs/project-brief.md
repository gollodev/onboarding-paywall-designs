# Project brief — Brotia

> Generado con `discover_project.py` (salida bruta: `project-brief.auto.md`, `discovery.json`, `brand.json`) y revisado
> por el agente (Fase 1). Cada afirmación cita su origen (`archivo:línea`, relativo a `examples/demo-app/`)
> o está marcada como **[SUPOSICIÓN]** / **[POR CONFIRMAR]**.
> ⚠️ Brotia es una **app ficticia** creada para demostrar la skill.

## 1. App
| Campo | Valor | Origen |
|---|---|---|
| Nombre | Brotia | `app.json:3`, `package.json:3` |
| Plataformas | iOS y Android | `app.json:7-8` (bundleIdentifier y package) |
| Stack | Expo (React Native) + RevenueCat | `package.json:8,17`, `README.md:17` |
| Problema que resuelve | A personas con poca experiencia se les mueren las plantas de interior: no saben qué planta tienen ni cuándo regarla | `README.md:3` |

## 2. Pantallas y funciones principales
| Pantalla / función | Evidencia | Origen |
|---|---|---|
| Mis plantas (Home) | ruta + string | `src/navigation/RootNavigator.tsx:16`, `src/i18n/es.json:2` |
| Identificar planta con foto | ruta + función del README | `src/navigation/RootNavigator.tsx:17`, `README.md:7` |
| Cuidados de la planta ("Riego cada N días") | ruta + string | `src/navigation/RootNavigator.tsx:18`, `src/i18n/es.json:4` |
| Recordatorios de riego | ruta + expo-notifications | `src/navigation/RootNavigator.tsx:19`, `package.json:9` |
| Diagnóstico de plagas con foto | ruta, bloqueada sin Pro | `src/navigation/RootNavigator.tsx:20`, `src/screens/DiagnoseScreen.tsx:4-8` |
| Diario de crecimiento con fotos | ruta, bloqueada sin Pro | `src/navigation/RootNavigator.tsx:21`, `src/screens/JournalScreen.tsx:4-7` |
| Guías de cuidado (luz, agua, temperatura) | función del README | `README.md:9` |

## 3. Gratis vs Premium (Brotia Pro)
| Función | Gratis | Pro | Origen / estado |
|---|---|---|---|
| Plantas | hasta 3 | ilimitadas | `src/premium/entitlements.ts:5,16-17`, `__tests__/premium.test.ts:4-8` |
| Identificación por foto | ✅ | ✅ | `README.md:7` — **[SUPOSICIÓN]** gratis (no hay bloqueo en el código); confirmado en la Fase 2 |
| Recordatorios de riego | ✅ (sus 3 plantas) | ✅ (todas) | `README.md:8` — **[SUPOSICIÓN]** gratis; confirmado en la Fase 2 |
| Guías de cuidado | ✅ | ✅ | `README.md:9` |
| Diagnóstico de plagas | — | ✅ | `src/screens/DiagnoseScreen.tsx:7-8`, `README.md:12` |
| Diario de crecimiento | — | ✅ | `src/screens/JournalScreen.tsx:7`, `README.md:13` |

Hoy el paywall se abre al tocar Diagnóstico o Diario (`source: 'diagnose_locked'` / `'journal_locked'`).

## 4. Identidad visual
| Elemento | Valor | Origen |
|---|---|---|
| Logo | Brote blanco sobre cuadrado verde redondeado | `assets/logo.svg`, `app.json:5` |
| Paleta clara | primary `#2F9E44`, accent `#F59F00`, bg `#FFFFFF`, surface `#F3F7F2`, text `#14201A`, muted `#5C6B62`, border `#DDE7DF` | `src/theme/colors.ts:3-9` |
| Paleta oscura | primary `#51CF66`, accent `#FFC34D`, bg `#0E1511`, surface `#18221C`, text `#EEF5F0`, muted `#9DB0A4`, border `#2A3A30` | `src/theme/colors.ts:12-18` |
| Tipografía | Nunito (400/700/800). En los diseños se usa **Poppins**, la más parecida entre las empaquetadas (Nunito no está en `assets/fonts`) | `src/theme/typography.ts:1-8` |
| Claro / oscuro | Ambos (sigue al sistema) | `app.json:6` (`userInterfaceStyle: automatic`), `src/navigation/RootNavigator.tsx:13` |
| Íconos | Lucide (trazo de 2 px), el mismo set que usa la skill | `package.json:14` |
| Tono | Cercano, tuteo, frases cortas y prácticas ("Añade tu primera planta y te diremos cuándo regarla.") | `src/i18n/es.json:2-7` |

## 5. Pagos
| Elemento | Valor | Origen |
|---|---|---|
| SDK | RevenueCat (`react-native-purchases`), entitlement `pro` | `package.json:17`, `src/premium/entitlements.ts:4` |
| Productos | `brotia.pro.monthly`, `brotia.pro.annual` (la prueba va ligada al anual) | `src/premium/products.ts:3-6` |
| Precios | No están en el código (se configuran en las tiendas). **Respuesta del usuario en la Fase 2:** $4.99/mes, $29.99/año, prueba de 7 días en el anual | Fase 2 (simulada) |

## 6. Idiomas y mercados
| Elemento | Valor | Origen |
|---|---|---|
| Idiomas | es, en | `src/i18n/es.json`, `src/i18n/en.json` |
| Idioma principal | español | `README.md:1` — **[SUPOSICIÓN]**, confirmado en la Fase 2 |
| Mercados probables | Latinoamérica y EE. UU. hispano (precios en USD) | **[SUPOSICIÓN]**, confirmado en la Fase 2 |

## 7. Preguntas que el código no respondía (Fase 2, respuestas simuladas)
- **Público y "momento ajá"**: principiantes con 1–10 plantas en casa que quieren que dejen de morirse. El momento ajá es el primer aviso de riego correcto.
- **Precios, moneda y prueba**: ver §5.
- **Prueba social real**: **aún no hay** (la app no tiene valoraciones publicadas). Se muestra un marcador visible y queda en pendientes.
- **Recordatorio antes de que termine la prueba**: la app lo envía (expo-notifications). Confirmado.
- **URLs de términos y privacidad**: **sin respuesta**. Quedan en pendientes.
- **Formato**: iPhone + Android, claro + oscuro, sin marco, 5 pantallas de onboarding y 4 paywalls, cada uno con una variante B.
