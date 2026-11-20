// Validate, classify, decide escalation, draft a reply.
// Mirrors PROJECT-01-CUSTOMER-SUPPORT/support.py so the two stay comparable.
const item = payload;
const email = String(item.customer_email || '').trim();
const body = String(item.body || '').trim();
const problems = [];

if (!item.external_id) problems.push('external_id is required');
if (!/^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$/.test(email)) problems.push('customer_email is not a valid email address');
if (body.length < 10) problems.push('body must be at least 10 characters');
if (problems.length) {
  return [{ outcome: 'rejected', external_id: item.external_id || null, problems }];
}

const text = `${item.subject || ''} ${body}`.toLowerCase();
const count = (words) => words.filter((w) => text.includes(w)).length;

const keywords = {
  complaint: ['damaged', 'broken', 'wrong item', 'not delivered', 'never arrived', 'late',
              'delayed', 'poor', 'terrible', 'unacceptable', 'angry', 'disappointed', 'faulty',
              'missing', 'expired', 'allergic', 'reaction', 'safety', 'health', 'contaminated'],
  billing: ['invoice', 'payment', 'charged', 'overcharged', 'receipt', 'statement',
            'credit note', 'refund', 'wrong price'],
  request: ['please send', 'could you', 'can you', 'need a', 'request', 'quotation',
            'price list', 'stock out', 'out of stock', 'completely out', 'run out', 'reorder'],
  feedback: ['suggestion', 'feedback', 'thank you', 'thanks', 'great service', 'well done'],
  inquiry: ['how do', 'what is', 'when will', 'do you', 'is there', '?'],
};

const scores = {};
for (const [name, words] of Object.entries(keywords)) scores[name] = count(words);
if (scores.complaint) scores.inquiry = 0;

const priority = ['complaint', 'billing', 'request', 'feedback', 'inquiry'];
let category = 'other';
let best = 0;
for (const name of priority) {
  if (scores[name] > best) { best = scores[name]; category = name; }
}
const needsReview = best === 0 ? 1 : 0;

const urgent = ['urgent', 'asap', 'immediately', 'right away', 'today', 'deadline',
                'critical', 'emergency', 'escalate', 'manager'];
const urgency = count(urgent) ? 'high' : (category === 'complaint' ? 'medium' : 'low');

const negative = count(['angry', 'unacceptable', 'terrible', 'disappointed', 'frustrated',
                        'poor', 'complaint', 'faulty', 'damaged', 'wrong']);
const positive = count(['thank', 'thanks', 'great', 'excellent', 'appreciate', 'happy']);
const sentiment = negative > positive ? 'negative' : (positive > negative ? 'positive' : 'neutral');

const sensitive = ['refund', 'compensation', 'legal', 'lawyer', 'sue', 'injury', 'health',
                   'safety', 'expired', 'allergic'];
const reasons = [];
if (count(sensitive)) reasons.push('mentions refund, compensation, legal, health or safety');
if (urgency === 'high') reasons.push('marked urgent by the sender');
if (category === 'complaint' && sentiment === 'negative') reasons.push('negative complaint');
if (text.includes('escalate') || text.includes('manager')) reasons.push('asks for a manager or escalation');

const escalate = reasons.length > 0;
const name = String(item.customer_name || 'Customer').split(' ')[0];
const ref = item.external_id;

const templates = {
  complaint: `Dear ${name},\n\nThank you for telling us about this, and I am sorry the order did not meet the standard you expected. I have logged your message as a formal complaint under reference ${ref}.\n\nWhat happens next: a member of the team will review the details and come back to you within one working day.\n\nKind regards,\nCustomer Support`,
  billing: `Dear ${name},\n\nThank you for your message about billing. I have logged it under reference ${ref} and passed the details to the accounts team.\n\nPlease confirm the invoice number and the date of the charge if you have them to hand. You will receive a written response within two working days.\n\nKind regards,\nCustomer Support`,
  request: `Dear ${name},\n\nThank you for your request. I have recorded it under reference ${ref} and the team will confirm what is possible and when.\n\nKind regards,\nCustomer Support`,
  feedback: `Dear ${name},\n\nThank you for taking the time to write. Your comments have been logged under reference ${ref} and shared with the team.\n\nKind regards,\nCustomer Support`,
  inquiry: `Dear ${name},\n\nThank you for your question. I have logged it under reference ${ref} so it can be answered properly.\n\nA colleague with the right detail will reply within one working day.\n\nKind regards,\nCustomer Support`,
  other: `Dear ${name},\n\nThank you for your message. It has been logged under reference ${ref} and a member of the team will review it.\n\nKind regards,\nCustomer Support`,
};

return [{
  outcome: 'accepted',
  external_id: ref,
  customer_email: email,
  category,
  urgency,
  sentiment,
  needs_review: needsReview,
  escalate,
  escalation_reason: reasons.join('; '),
  status: escalate ? 'escalated' : 'awaiting_approval',
  draft_subject: `Re: ${item.subject || 'your message'}`,
  draft_body: templates[category] || templates.other,
  approved: false,
}];
