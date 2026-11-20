// Score a lead against published criteria and draft a band-matched follow-up.
// Mirrors PROJECT-03-SALES-AUTOMATION/leads.py.
const item = payload;
const problems = [];

if (!item.external_id) problems.push('external_id is required');
if (!item.name || String(item.name).trim().length < 2) problems.push('name is required');
const email = String(item.email || '').trim();
if (!/^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$/.test(email)) {
  problems.push('email is not a valid email address');
}
if (problems.length) {
  return [{ outcome: 'rejected', external_id: item.external_id || null, problems }];
}

const parts = [];
const add = (label, points) => parts.push({ label, points });

const sourcePoints = { referral: 15, website: 10, linkedin: 8, event: 6, 'cold-list': 2, other: 0 };
const source = String(item.source || 'other').toLowerCase();
add(`source ${source}`, sourcePoints[source] ?? 0);

const budget = item.budget === null || item.budget === undefined || item.budget === ''
  ? null : Number(item.budget);
if (budget === null) add('no budget stated', 0);
else if (budget >= 5000) add('budget 5,000+', 20);
else if (budget >= 1000) add('budget 1,000-4,999', 12);
else if (budget > 0) add('budget under 1,000', 5);
else add('budget stated as zero', 0);

const timeline = String(item.timeline || '').toLowerCase();
const timelineRules = [['immediate', 15], ['now', 15], ['this month', 15],
                       ['1-3 months', 10], ['next quarter', 10], ['later', 3]];
const timelineHit = timelineRules.find(([phrase]) => timeline.includes(phrase));
add(timelineHit ? `timeline '${timelineHit[0]}'` : 'timeline unknown', timelineHit ? timelineHit[1] : 3);

const role = String(item.role || '').toLowerCase();
const roleRules = [['owner', 10], ['founder', 10], ['director', 10], ['head', 10],
                   ['ceo', 10], ['manager', 6]];
const roleHit = roleRules.find(([phrase]) => role.includes(phrase));
add(roleHit ? `role '${roleHit[0]}'` : 'role not decision maker', roleHit ? roleHit[1] : 2);

const employees = item.employees === null || item.employees === undefined || item.employees === ''
  ? null : Number(item.employees);
if (employees === null) add('company size unknown', 2);
else if (employees >= 50) add('company 50+ staff', 8);
else if (employees >= 10) add('company 10-49 staff', 5);
else add('company under 10 staff', 2);

const complete = ['email', 'company', 'message'].filter((f) => item[f]).length;
add(`${complete}/3 contact details complete`, complete === 3 ? 5 : 0);

const score = parts.reduce((sum, p) => sum + p.points, 0);
const band = score >= 60 ? 'A' : (score >= 35 ? 'B' : 'C');
const segment = (employees || 0) >= 50 || (budget || 0) >= 5000
  ? 'key account'
  : ((employees || 0) >= 10 || (budget || 0) >= 1000 ? 'growth' : 'small');

const first = String(item.name).trim().split(' ')[0];
const topic = String(item.message || 'your enquiry').split(/[.!?\n]/)[0].trim().toLowerCase().slice(0, 90);

const bodies = {
  A: `Dear ${first},\n\nThank you for getting in touch about ${topic}. The next useful step is a short call to confirm volumes, delivery points and timing, so I can put a proper quotation together.\n\nKind regards,\nKelvin`,
  B: `Dear ${first},\n\nThank you for your enquiry about ${topic}. I can share our current price list and lead times. Could you confirm roughly how often you would order and whether delivery is to one site or several?\n\nKind regards,\nKelvin`,
  C: `Dear ${first},\n\nThank you for your message about ${topic}. I have added your details to our list and will send relevant updates as they come up.\n\nKind regards,\nKelvin`,
};

return [{
  outcome: 'accepted',
  external_id: item.external_id,
  name: item.name,
  email,
  company: item.company || null,
  source,
  score,
  band,
  segment,
  score_reason: parts.map((p) => `${p.label} +${p.points}`).join('; '),
  status: 'new',
  draft_subject: `Following up on your enquiry (${item.company || item.name})`,
  draft_body: bodies[band],
  approved: false,
}];
