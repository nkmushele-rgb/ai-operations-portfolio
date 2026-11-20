# Cost notes

## Local portfolio

Running the three Python projects costs **nothing** beyond a computer and
Python. No paid API is used. The optional model runs locally through Ollama, so
there is no per-token charge.

Verified locally on 20 November 2026:

| Item | Cost |
|---|---|
| Python 3.12 | Free |
| Standard-library modules used here | Free |
| SQLite | Free, included with Python |
| Ollama with a local model | Free, uses local hardware |
| Node.js (only for the rules checks) | Free |
| Make account | Not connected; no cost incurred here |
| Google Sheets / Gmail modules in the specs | Inactive; no account connected |

## If the learner adds a hosted platform

These are **not** costs of the portfolio and must be date-stamped if quoted to
anyone. Checked against official sources in November 2026:

| Service | Verified position | Source |
|---|---|---|
| Make paid plans | Prices and allowances change; check the current plans before quoting | `https://www.make.com/en/pricing` |
| Zapier Free | 100 tasks/month, 2-step Zaps | `https://zapier.com/pricing` |
| HubSpot CRM Free | Free tier with a real API | `https://developers.hubspot.com/docs/api/crm/contacts` |
| WhatsApp Cloud API | Charged per delivered message by category and market; prices changed 1 October 2026 | `https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing` |

Prices change. Re-check them before quoting a client. Do not present these as
the learner's costs: none of these accounts are connected to the portfolio.

## When a client asks for a production estimate

Do not invent a number. The honest framing is:

> "The portfolio runs at zero marginal cost locally. A production version
> depends on the platform, message volume and which accounts are connected. I
> would price that after a short discovery step, and I would set a spend cap and
> a human approval step before any external action."

## Spend guardrails for any future paid setup

- Provider-side spend cap and rate limit before going live.
- Credentials in the platform store or a git-ignored `.env`, never in a file.
- Human approval before sending messages, changing CRM records or spending money.
- Opt-in and opt-out paths for any messaging channel.
