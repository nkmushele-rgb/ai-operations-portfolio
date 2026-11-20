# Demo talk track

Three short walkthroughs. Total running time about six minutes. Keep the browser
on the dashboard, not the code, unless the viewer asks to see the implementation.

## Before the call

- [ ] Run `python run.py demo` then `python run.py dashboard` in each project.
- [ ] Serve the folder: `python -m http.server 8099 --bind 127.0.0.1`.
- [ ] Check all three dashboards load and the images render.
- [ ] Have `DOCUMENTATION/limitations-and-honesty.md` open for the final question.
- [ ] Say at the start: "These are portfolio projects with synthetic data."

## Project 1 — customer support triage (2 minutes)

1. **Open the dashboard.** Point to the counts: 9 accepted, 3 rejected, 4 escalated.
2. **The problem.** "A distributor gets the same questions all day. Urgent ones
   sit behind routine ones, and a safety complaint can be answered by whoever
   is free."
3. **The rule.** "I classify with keywords, not the model, because I want the
   same message to route the same way every time. Refund, legal, health, safety
   or 'urgent' means a human gets it."
4. **The control.** Scroll to an escalated row. "This one is escalated. Even if
   someone approves it, `send()` refuses it. I have a test for that."
5. **The model.** "The model writes the wording only. Turn it off and the demo
   still runs, using templates."
6. **The limit.** "Three messages were rejected by validation, and one vague one
   is flagged for review instead of guessed at. Keyword rules need a labelled
   set of real messages before I would trust them in production."

## Project 2 — inventory and stock control (2 minutes)

1. **Open the dashboard.** Point to stock value, low stock and open alerts.
2. **The problem.** "Distributors oversell, miss stockouts and lose track of
   shrinkage because balances get edited in place."
3. **The record.** "Every receipt, issue and adjustment is a row. The balance is
   a cache; the movements are the truth."
4. **The refusal.** Show the rejected row. "This asks for 30 cases with 28 on
   hand. It is refused and logged, not silently zeroed."
5. **The valuation.** "Moving average, not FIFO, because a small distributor can
   check one number against the last invoice."
6. **The limit.** "No batches or expiry dates. That would be my first upgrade for
   a dairy business."

## Project 3 — sales lead management (2 minutes)

1. **Open the dashboard.** Point to the ranking and the points breakdown.
2. **The problem.** "Every enquiry gets the same reply, so a forty-site contract
   waits behind a one-shop price request."
3. **The score.** "Six rules, maximum 73 points. Every lead stores the arithmetic,
   so a salesperson can argue with a threshold instead of being told 'the model
   said so'."
4. **The duplicate.** "This buyer came back under a new reference. It is matched
   on email and attached to the original lead."
5. **The control.** "The follow-up is written but `approved` is false. `send()`
   refuses it until a named person approves."
6. **The limit.** "The scores are defensible, not calibrated. There is no won/lost
   history to fit them to."

## Closing line

> "What I am offering is not a senior AI engineer. It is someone who has run
> operations, knows where the records go wrong, and can build a small automation
> that is explicit, tested and safe to hand over. I would start with a paid trial
> on one real process."

## Questions likely to come up

| Question | Short answer |
|---|---|
| "Why not just use ChatGPT?" | It does not keep records, refuse an oversell or enforce an approval. Those need rules and tests. |
| "Can you connect our CRM?" | Not connected yet. The exports have disabled nodes ready for credentials; connecting them is the first paid task. |
| "Did a client pay for these?" | No. They are portfolio work. I will not claim otherwise. |
| "How much does it cost?" | The local portfolio is free. Production pricing depends on platform and volume; I would set a cap first. |
| "Can you show the tests?" | Yes — 90 tests, with the failure cases listed in each `test-cases.md`. |
