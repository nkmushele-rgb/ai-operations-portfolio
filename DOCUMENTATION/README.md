# Documentation index

| File | Use it when |
|---|---|
| `setup-and-run.md` | You want to run the projects from a fresh Python install. |
| `testing-summary.md` | You need to know what the 90 tests cover and what they do not. |
| `make-verification.md` | You need the honest status of the scenario specs and what would count as verification. |
| `make-build-guide.md` | You want to build each scenario in a Make account from the shipped specification. |
| `limitations-and-honesty.md` | You are writing a profile, CV, proposal or cover letter. |
| `cost-notes.md` | A client or recruiter asks what this costs to run. |

## The short version

- Three projects, standard-library Python only, Python 3.10+.
- 90 passing tests, covering happy path, invalid input, missing data, model
  failure and control failures.
- Each project has a generated dashboard from a real demo run and a real screenshot.
- Each project has a Make build specification whose reference rules are executed
  under Node and compared with the Python logic. Nothing has run inside Make.
- All data is synthetic. No client work, no client results, no personal data.
