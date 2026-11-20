# Hubstaff profile audit — checklist

The account was not accessible when this folder was prepared: the Hubstaff tab
redirects to a sign-in page with the email pre-filled and the password blank.
Only the learner can sign in. Do not ask for or store the password.

## 1. Sign in and capture the current state

- [ ] Learner signs in to Hubstaff Talent.
- [ ] Save a screenshot of the current profile before any edit.
- [ ] Record the current title, overview, skills, rate and availability here.

Current title before edit: *(blank)*

Current rate before edit: *(blank)*

Current availability before edit: Hourly ($/hour)

### Applied on 20 November 2026

A draft profile already existed at `/profiles/kelvin-nyinge` with the account
name "Kelvin Nyinge", location "Doha, Qatar, Qatar", 0 years, no skills, no
languages and no bio. The wizard's step 2 (Details) and step 3 (Web presence)
were completed and saved. Step 4 (Resume) was skipped deliberately: the CV
still contains unconfirmed employment dates.

Public URL now: <https://hubstafftalent.net/profiles/kelvin-mushele> (the old
`kelvin-nyinge` slug redirects)

- Title: `AI OPERATIONS ASSISTANT | AI WORKFLOW AUTOMATION | REMOTE BUSINESS OPERATIONS`
- Experience: 10 years
- Languages: English
- Skills (10, the platform maximum): Lead Generation, Python, SQL, Customer
  Service, Business Operations, Excel, Automation, Workflow, Inventory
  Management, Operations Management
- Websites: Code samples → `https://github.com/nkmushele-rgb`
- Avatar: neutral "KM" monogram placeholder. Replace with a real photo.
- Rate and availability were left untouched.

Substitutions forced by Hubstaff's taxonomy (requested term does not exist):
n8n → Workflow + Automation (n8n is no longer part of the positioning); Customer
Support → Customer Service; Process
Improvement → Process Management (not selected in the final 10); Microsoft
Excel → Excel; REST APIs → REST (not selected); Prompt Engineering → not
offered; Business Process Automation → Automation + Business Operations.

## 2. Compare against the draft

| Field | Target | Agreed change? |
|---|---|---|
| Title | `AI OPERATIONS ASSISTANT \| AI WORKFLOW AUTOMATION \| REMOTE BUSINESS OPERATIONS` | [ ] |
| Category | Virtual Assistant / Admin / Business Process Automation | [ ] |
| Overview | Text in `hubstaff-profile-draft.md` | [ ] |
| Skills | Top 15 in `hubstaff-profile-draft.md`, valid taxonomy terms only | [ ] |
| Uploads | Portfolio website plus three project READMEs | [ ] |
| Availability | Remote, Qatar-based, paid trial task accepted | [ ] |
| Rate | Learner decides | [ ] |

## 3. Check before changing

- [ ] Every skill term exists in Hubstaff's typeahead. If it does not, use the
      nearest valid term and note the substitution.
- [ ] No invented qualification, employer, date, certification or result.
- [ ] Portfolio links resolve in a signed-out browser tab.
- [ ] No screenshot or file contains an API key, webhook URL, token or personal data.
- [x] The website contact details are real (email and GitHub only).
- [ ] No "importable" or "tested in Make" claim; see `DOCUMENTATION/make-verification.md`.

## 4. Apply only after approval

- [x] Learner approved the display name "Kelvin Mushele" and "Doha, Qatar".
- [x] Learner said to proceed ("/ready"); title and overview came from the
      approved draft and use only verified employer names.
- [ ] Rate and availability still need an explicit commercial decision.
- [x] Applied in one session and re-read the public profile.
- [x] Screenshot saved by the browser tool on 20 November 2026.

### Name, location and DOB — resolved

- The account last name was changed from "Nyinge" to "Mushele" with explicit
  approval. The account now reads "Welcome, Kelvin Mushele".
- That alone did **not** change the Talent profile name. Once the wizard was
  finished, "Edit profile" stopped redirecting to step 2 and opened a full
  edit form at `/profiles/kelvin-nyinge/edit` with name, country, state, city
  and DOB fields. The name was set to "Kelvin Mushele" and saved.
- Canonical public URL is now <https://hubstafftalent.net/profiles/kelvin-mushele>.
  The old `/profiles/kelvin-nyinge` URL redirects to it.
- Location was already correct: the public display order is **city, state,
  country**, and the stored values are city `Doha`, state `Qatar`, country
  `QA`. It only looked wrong before the full edit form was visible.
- A date of birth (2 September 1990) was already stored and "hide age on
  profile page" is ticked. No date was invented or changed.
- The account time zone is `Asia/Kolkata`, which does not match Qatar. Left
  untouched; raise it with the learner before quoting availability.

### Still open after the session

- The **live bio was updated on 20 November 2026** under the learner's approved
  platform switch. The old sentence "I use n8n for the workflow layer…" was
  replaced with "I design Make scenarios from written specifications, build the
  logic in Python and SQLite, and use a local model only to write prose." The
  profile page was re-read: it contains "Make scenarios", no "n8n", and the
  title, 10 skills, English, 10 years and GitHub link are unchanged.
- A signed-out tab returned "Profile not found — the profile is not public or
  does not exist" for both profile URLs, while the edit form shows privacy
  `Everyone`. A signed-in "View profile" renders correctly. Treat anonymous
  visibility as unverified; do not promise a recruiter that the public link
  works until the learner checks it in a browser with no login.
- Portfolio website was published on 20 November 2026. On the same day the
  `Portfolio site` field was added and the signed-in profile page was re-read:
  it links to <https://nkmushele-rgb.github.io/ai-operations-portfolio/>.
- Resume replaced on 20 Nov: the PDF generated from the learner's edited copy is
  attached (ID 555698) and its SHA256 matches the local file. The old record
  (`/resumes/555664`) returns 404. Profile pay rate reads $40/hr; the learner
  confirmed on 20 Nov that they set it and the agent did not change it.
- Pay rate and availability are blank / "Hourly ($/hour)" by default; these are
  commercial decisions for the learner.
- The "KM" monogram avatar is a placeholder; replace with a real photo.

## 5. After the profile

- [ ] Use `../JOB-APPLICATIONS/job-suitability.md` to choose target roles.
- [ ] Use `../JOB-APPLICATIONS/application-letter-templates.md` for the first three applications.
- [ ] Log each application in `../JOB-APPLICATIONS/Application-Tracker.xlsx`.

## Observed platform behaviour

Recorded on 20 November 2026:

- The profile wizard URL `hubstafftalent.net/wizards/profiles/new` redirects to
  `account.hubstaff.com/login`.
- The login form has the email pre-filled and the password empty.
- The accessibility tree on that page is nearly empty, so form work needs
  DOM-level interaction rather than accessibility refs.

Re-check these details before relying on them; platforms change.
