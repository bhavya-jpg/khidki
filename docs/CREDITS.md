# Credits and licences

Khidki is Apache-2.0. It stands on the work below. Anything not listed here was written during the
event (8 to 11 Oct 2026).

## Data
| Source | Use | Licence / terms |
|---|---|---|
| Open-Meteo Air Quality API, CAMS European/Global ENSEMBLE | outdoor PM2.5, PM10, CO₂ forecast and replay days | CC BY 4.0; attribution required: "Contains modified Copernicus Atmosphere Monitoring Service information" and "Weather data by Open-Meteo.com" |
| Open-Meteo Weather API | outdoor temperature, humidity, wind, rain | CC BY 4.0 |
| CPCB real-time AQI via data.gov.in (resource `3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69`) | nowcast for bias correction | Government Open Data Licence, India (GODL-India) |

## Libraries
Filled in as each library is added.

| Library | Licence |
|---|---|
| NumPy | BSD-3-Clause |
| Pydantic | MIT |
| pytest | MIT |
| Ruff | MIT |
| mypy | MIT |
| FastAPI, Starlette, Uvicorn | MIT, BSD-3-Clause, BSD-3-Clause |
| PyYAML | MIT |
| React, React Router | MIT |
| Vite, @vitejs/plugin-react | MIT |
| TypeScript | Apache-2.0 |
| Playwright (screenshots) | Apache-2.0 |
| Anek Latin, Anek Devanagari (Ek Type, Google Fonts) | SIL Open Font License 1.1 |

## Research
See `docs/physics.md` for the papers behind every parameter.

## AI coding tools
Built with **Claude Code** (Anthropic) in VS Code.
| Cedar (cedarpy bindings) | Apache-2.0 |
| Strands Agents SDK | Apache-2.0 |
| boto3 / botocore | Apache-2.0 |
| moto (tests) | Apache-2.0 |
| Matplotlib (benchmark chart) | Matplotlib licence (PSF-based) |

## Explainer video (`video/`)
| Tool | Use | Licence / terms |
|---|---|---|
| Remotion | motion graphics and rendering | Remotion licence: free for individuals and teams of up to three |
| Chatterbox (Resemble AI) | the narration: a synthetic voice, generated locally and said to be so on screen | MIT |
| OpenAI Whisper | transcribing the narration back to check it | MIT |
| Playwright, FFmpeg | capturing the real teacher screen from local mode | Apache-2.0; LGPL/GPL (used as a tool, not distributed) |
| Agent skills from `remotion-dev/skills` and `heygen-com/hyperframes` | guidance for the coding agent; installed locally, not committed (`skills-lock.json`) | see each repository |
