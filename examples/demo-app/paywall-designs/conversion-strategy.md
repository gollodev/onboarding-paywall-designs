# Conversion strategy — Brotia

> Basada en `project-brief.md` y en las respuestas (simuladas) de la Fase 2. Cada decisión lleva su **Por qué** en una línea.
> Brotia es una app ficticia: los precios y respuestas son de ejemplo.

## 1. Mapa del viaje (instalación → pago)
| Paso | Pantalla(s) | Objetivo del usuario | Nuestro objetivo | Por qué |
|---|---|---|---|---|
| Primera apertura | 01-welcome | Saber si la app le sirve | Prometer el resultado en 5 palabras | La claridad sobre el resultado reduce el abandono en la primera pantalla |
| Primer valor (ajá) | 02-benefit | Ver qué hace la app | Mostrar identificación + aviso de riego | El ajá de Brotia es "sé qué planta tengo y cuándo regarla" (`README.md:3`) |
| Personalización | 03-personalization | Contar qué quiere | Guardar `answers.goal` | Su respuesta se repite en la pantalla puente y en el paywall (compromiso y coherencia) |
| Permiso | 04-permissions | Entender por qué avisos | Explicar el beneficio antes del diálogo del sistema; "Ahora no" visible | Pedir permiso con contexto mejora la aceptación sin forzar |
| Puente | 05-bridge | Ver "su plan" | Conectar su objetivo con Pro, separando gratis y Pro | Llega al paywall sabiendo qué es gratis y qué añade Pro (sin sorpresas) |
| Paywall | 10-paywall-trial (fin del onboarding), 13-paywall-locked (al tocar Diagnóstico) | Decidir sin miedo | Inicio de prueba | Dos momentos de intención distintos, dos diseños |
| Primeras sesiones | (en la app) | Añadir plantas y recibir el primer aviso | Llegar a 3 plantas (límite gratis) | El límite de 3 plantas (`entitlements.ts:5`) es el siguiente punto natural para mostrar 11/12 |

## 2. Onboarding que prepara la venta
- **Pregunta de personalización:** "¿Qué quieres conseguir con tus plantas?". La opción "Que dejen de morirse" se guarda como `answers.goal = "mantener vivas tus plantas"` y se repite en 05-bridge ("Tu plan para mantener vivas tus plantas") y en la variante B de 10 ("Tu plan para mantener vivas tus plantas").
- **Demostración de valor:** 02-benefit enseña identificación con foto + calendario + avisos. Son funciones gratis, así que se muestra valor real antes de pedir nada.
- **Pantalla puente:** 05-bridge lista lo que incluye su plan y marca honestamente "Gratis, hasta 3 plantas" frente a "Con Brotia Pro".

## 3. Anatomía del paywall
| Elemento | Contenido | Por qué |
|---|---|---|
| Titular (resultado) | "Mantén vivas todas tus plantas" / "Cuida todas tus plantas, no solo 3" | Resultado + ancla en el límite gratis real (3 plantas) |
| Beneficios (3–4) | Plantas ilimitadas · Diagnóstico de plagas con foto · Diario de crecimiento · Recordatorios para todas | Solo funciones Pro reales (`entitlements.ts:6`, `README.md:11-13`) |
| Prueba social | **Marcador "PRUEBA SOCIAL REAL PENDIENTE"** en 12 | No hay valoraciones reales; no se inventan |
| Plan recomendado + ahorro | Anual destacado, "Ahorra 49%" (= 1 − 29,99 / (4,99 × 12), redondeado hacia abajo), "equivale a $2.49/mes" en tamaño secundario | Anclaje de precio con cifras reales; el importe facturado es lo más visible |
| CTA único | "Empezar mis 7 días gratis" (o "Suscribirme por $4.99/mes" si se destaca el mensual) | El texto dice exactamente qué pasa al tocar |
| Línea de transparencia | "Hoy no pagas nada. Te avisaremos 2 días antes de que termine tu prueba." | Reduce el miedo a cobros sorpresa; la app sí envía el aviso (confirmado) |
| Elementos obligatorios | Cerrar, Restaurar compras, precio + periodo, condiciones de la prueba, renovación automática, cómo cancelar, Términos, Privacidad | `references/store-rules.md`; verificados por `quality_checks.py` |

## 4. Principios aplicados
- **Claridad sobre el resultado:** los titulares hablan de plantas vivas, no de funciones.
- **Anclaje de precios:** el mensual aparece junto al anual en 10, 11 y 12, y el ahorro se calcula solo con precios reales.
- **Reducción de riesgo:** el timeline (Hoy → Día 5 aviso → Día 7 cobro), "Cancela cuando quieras" e instrucciones exactas de cancelación por plataforma.
- **Personalización:** el objetivo elegido se repite en el puente y en la variante 10-B.
- **Jerarquía / un solo camino:** un botón principal por pantalla. Cerrar y Restaurar están visibles, pero son secundarios.
- **Urgencia:** **ninguna** (`urgency.real = false`). No hay ofertas con fecha real.

## 5. Objeción → elemento del diseño
| Objeción | Elemento que la responde | Pantalla |
|---|---|---|
| "Es caro" | Anual con "equivale a $2.49/mes" y "Ahorra 49%" frente al mensual | 10, 11, 12 |
| "Me van a cobrar sin avisar" | Timeline de la prueba + "Hoy no pagas nada" + aviso 2 días antes | 10, todas con prueba |
| "Con 3 plantas me basta" | Titular "no solo 3" + plan gratis presentado con honestidad en el puente | 05, 11 |
| "¿Funciona de verdad?" | Demostración en 02; prueba social real **pendiente** | 02, 12 |
| "No sé cancelar" | "Cancela cuando quieras en Ajustes › Apple ID › Suscripciones" / "Google Play › Pagos y suscripciones" | Todas |

## 6. Hipótesis A/B
| Paywall | Variante | Qué cambia | Hipótesis | Métrica |
|---|---|---|---|---|
| 10-paywall-trial | B | Titular personalizado "Tu plan para {{answers.goal}}" | Repetir su objetivo aumenta el inicio de prueba | paywall → inicio de prueba |
| 11-paywall-plans | B | Plan destacado: mensual | Baja la fricción de precio y sube la conversión, aunque puede bajar el ingreso por usuario | conversión del paywall e ingreso por usuario a 30 días |
| 12-paywall-benefits | B | Orden de beneficios: diagnóstico primero | El dolor más urgente (planta enferma) convierte más que "ilimitadas" | paywall → inicio de prueba |
| 13-paywall-locked | B | Plan destacado: mensual sin prueba | Con intención alta (función bloqueada), el pago directo convierte más | conversión a pago directo y reembolsos |

## 7. Patrones prohibidos: autocomprobación
- [x] Botón de cerrar visible desde el primer momento, con contraste ≥ 3:1 (comprobado automáticamente)
- [x] El precio facturado es lo más visible y el periodo siempre va junto al precio
- [x] La prueba muestra el precio posterior y el día del cobro
- [x] Sin urgencia, escasez ni cuenta regresiva falsas
- [x] Sin testimonios, valoraciones, cifras ni prensa inventados (marcador visible)
- [x] Sin CTA engañoso ni "confirmshaming" ("Ahora no" neutro en la pantalla de permisos)
