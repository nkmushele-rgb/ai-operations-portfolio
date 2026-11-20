# Limitations and honesty

Read this before writing a profile, CV, proposal, cover letter or interview
answer. It is the line between evidence and invention.

## What is true

- The three projects were built, run and tested locally.
- The data is synthetic, written into the sample files in each `data/` folder.
- The dashboards were generated from real demo runs and screenshotted from a
  browser; they were not designed as mock-ups.
- 90 automated tests pass, plus the workflow structure and reference-rule checks.
- The three Make build specs are structurally valid and their reference rules
  execute under Node.

## What is not true, and must never be claimed

- That any of this was built for a paying client.
- That it saved someone hours, money or stock.
- That any certification was earned, or that Make, HubSpot or any vendor endorsed it.
- That the author is a senior AI engineer. The positioning is an operations
  practitioner moving into automation.
- That the scenarios were built, imported or executed inside Make, until
  `make-verification.md` says so.
- That a mailbox, CRM, Google Sheet or WhatsApp number is connected. None is.

## Project limitations, in one place

| Project | Limits |
|---|---|
| Support triage | Keyword rules misread unusual phrasing; one vague message is flagged, not resolved; no mailbox; no dedupe on customer plus subject. |
| Inventory | Moving average, not FIFO; no batch or expiry tracking; no locations; fixed anomaly thresholds; alerts are stored, not sent. |
| Sales | Scores are not calibrated to real conversions; thresholds are judgement calls; budget is unverified; exact-email dedupe only; no sequencing. |
| All three | Generated dashboards, not live apps; no authentication, rate limiting or concurrency proof. |

## Interview answers that stay honest

**"Tell me about a client result."**
"I have not delivered a paid client automation yet. What I can show is three
end-to-end projects I built and tested, with the rules and limitations written
down. I would start a paid engagement with a small, measurable trial."

**"How do you use AI?"**
"I use a local model to draft prose. I deliberately do not let it classify a
complaint, score a lead or decide stock. Those are rules, because I want to
explain and test them. The workflows still work when the model is off."

**"Is this production-ready?"**
"Not yet. It is portfolio-grade. Before production I would add authentication,
credentials, retries, monitoring, a cost cap and a human approval point for
irreversible actions. Those gaps are listed in the architecture notes."

## Safe-to-publish checklist

- [x] Synthetic or public data only.
- [x] No API keys, tokens, webhook URLs, passwords or personal data in files or screenshots.
- [x] Placeholder contact details replaced before the site went live.
- [ ] Employment dates, territory and qualification years confirmed by the learner.
- [x] No client results, savings or performance figures.
- [x] Limitations visible on the website and in each project README.
- [x] Make claim matches `make-verification.md`; no "importable" or "tested in
      Make" wording.
