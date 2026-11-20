# Role suitability and gap analysis

Fit is scored against **evidence in this portfolio**, not against ambition.
5 = direct evidence, 1 = no evidence. A low score is a reason to build more
evidence, not a reason to exaggerate.

## Role families

| Role family | Fit | Evidence to lead with | Main gap | Apply? |
|---|---|---|---|---|
| AI operations assistant / workflow automation assistant | 5 | All three projects, 90 tests, approval gates, Make build specs | No live client deployment | **Yes — first choice** |
| Business process automation specialist (no-code/low-code) | 4 | Make scenario specs, rule-based decisions, test evidence | No scenario built in a Make account | **Yes** |
| Remote operations assistant with inventory/stock focus | 4 | Project 2 plus TRAGS stores experience | No ERP/WMS system named | **Yes** |
| Sales operations / lead management assistant | 4 | Project 3, route sales and account development | No CRM connected; HubSpot learning | **Yes, avoid HubSpot-hard roles** |
| Support operations / customer support triage | 4 | Project 1, escalation rules, approval gate | No real mailbox or ticket system | **Yes** |
| Supply chain / purchasing coordinator | 3 | FMCG distribution, stores, Project 2 | No named ERP/WMS; often location-restricted | Selective |
| AI data quality / AI evaluation task worker | 3 | Supply chain domain, Python, written tests | Formal assignment and strict eligibility | Second stage |
| Virtual assistant, general admin | 2 | Excel, reliability, operations background | Underuses the portfolio; low rate | Only as a stopgap |
| Data entry clerk | 1 | Accuracy | No evidence of volume or speed; low rate | No |
| Executive assistant / project manager | 1 | — | No project-management evidence | No |
| Senior AI / ML engineer | 1 | Local model used for prose | No model training, no production ML | No |

## How to read a job advert in 60 seconds

Score one point for each answer that is "yes":

1. Does it ask for workflow automation or no-code tools? (Make build spec)
2. Does it ask for Python, SQL, JSON, CSV or APIs? (three projects)
3. Does it involve operations, stock, support or leads? (direct evidence)
4. Does it value documentation, testing or process improvement? (README, tests, architecture)
5. Does it allow a portfolio project in place of a paid client case study? (demo pages)
6. Is the location/time zone compatible with Qatar? (check the advert)
7. Is any "learning" skill a hard requirement? If yes, subtract two.
8. Is a named ERP, WMS or CRM system a hard requirement? If yes, subtract one.

Apply at 5 and above. At 3–4, apply only if the trial task is paid and small.
Below 3, skip.

## Gap analysis

### Gaps that can be closed with existing assets

| Gap | Asset that answers it |
|---|---|
| "Show me something you built" | Three dashboards and READMEs, linked from the website |
| "How do you handle mistakes?" | Rejection tables, escalation rules, approval tests |
| "Do you write tests?" | 90 tests and `test-cases.md` files |
| "Can you explain the logic?" | `score_reason` stored on every lead; architecture notes |
| "Do you use AI responsibly?" | Rules decide, model drafts, human approves |

### Gaps that cannot be hidden

| Gap | Honest line to use |
|---|---|
| No paid client work | "These are portfolio projects. I would start with a paid trial on one of your processes." |
| Make not built or live-verified | "These are Make scenario build specifications. The rules are executed and cross-checked against the Python code. I have not yet built the scenarios in Make." |
| HubSpot API still learning | "I have not connected a live HubSpot instance yet. I would do that as part of the trial." |
| No ERP/WMS evidence | "My systems of record were route sheets, stock cards and site permits. Which system does this role use?" |
| No dates in the CV yet | Confirm with the learner before sending anything. |

### What to build next, in order

1. **Build the Make scenarios** from the specs, export blueprints, capture canvas screenshots, then update `../DOCUMENTATION/make-verification.md`.
2. **Publish the website** and put the URL in the CV and profile.
3. **Add one scored case study** describing a real process from the FMCG or stores work, with the rules written out, using no client data.
4. **Learn the HubSpot contacts API** only if the first ten applications keep asking for it.

## Tracking

Use `Application-Tracker.xlsx`. Record the fit score from the 8-point check
above in the "Fit" column so patterns are visible after a few weeks. If most
rejections cite the same gap, close that gap instead of sending more of the same
application.
