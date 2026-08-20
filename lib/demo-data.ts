import type { Industry, IndustryDemo, TranscriptTurn } from "./types";

const healthcare: TranscriptTurn[] = [
  { speaker: "Clinician", role: "primary", time: "00:04", raw: "Good morning, I’m Dr. Anika Rao. What brings you in today?", safe: "Good morning, I’m [CLINICIAN_1]. What brings you in today?", entities: [{ raw: "Dr. Anika Rao", token: "[CLINICIAN_1]", type: "PERSON" }] },
  { speaker: "Patient", role: "secondary", time: "00:11", raw: "I’m Arjun Mehta, date of birth 12 March 1982. My MRN is BLR-482791.", safe: "I’m [PATIENT_1], date of birth [DOB_1]. My MRN is [MRN_1].", entities: [{ raw: "Arjun Mehta", token: "[PATIENT_1]", type: "PERSON" }, { raw: "12 March 1982", token: "[DOB_1]", type: "DOB" }, { raw: "BLR-482791", token: "[MRN_1]", type: "MRN" }] },
  { speaker: "Patient", role: "secondary", time: "00:19", raw: "I have had a dry cough and mild fever for three days. Temperature was 100.4 degrees last night.", safe: "I have had a dry cough and mild fever for three days. Temperature was 100.4 degrees last night.", entities: [] },
  { speaker: "Clinician", role: "primary", time: "00:31", raw: "Any shortness of breath, chest pain, or known exposure?", safe: "Any shortness of breath, chest pain, or known exposure?", entities: [] },
  { speaker: "Patient", role: "secondary", time: "00:44", raw: "No chest pain. You can reach me at +91 98765 43210. I take metformin 500 milligrams twice daily.", safe: "No chest pain. You can reach me at [PHONE_1]. I take metformin 500 milligrams twice daily.", entities: [{ raw: "+91 98765 43210", token: "[PHONE_1]", type: "PHONE" }] },
  { speaker: "Bystander", role: "unknown", time: "00:56", raw: "I’m his daughter Nisha. We live at 18 Palm Grove Road, Indiranagar.", safe: "I’m his daughter [FAMILY_MEMBER_1]. We live at [ADDRESS_1].", entities: [{ raw: "Nisha", token: "[FAMILY_MEMBER_1]", type: "PERSON" }, { raw: "18 Palm Grove Road, Indiranagar", token: "[ADDRESS_1]", type: "ADDRESS" }] },
];

const finance: TranscriptTurn[] = [
  { speaker: "Agent", role: "primary", time: "00:04", raw: "Hello, I’m Rhea Singh from NorthBank support. How can I help?", safe: "Hello, I’m [AGENT_1] from [BANK_1] support. How can I help?", entities: [{ raw: "Rhea Singh", token: "[AGENT_1]", type: "PERSON" }, { raw: "NorthBank", token: "[BANK_1]", type: "ORG" }] },
  { speaker: "Customer", role: "secondary", time: "00:12", raw: "I’m Karan Malhotra. My customer ID is NB-482791 and PAN is ABCDE1234F.", safe: "I’m [CUSTOMER_1]. My customer ID is [CUSTOMER_ID_1] and PAN is [TAX_ID_1].", entities: [{ raw: "Karan Malhotra", token: "[CUSTOMER_1]", type: "PERSON" }, { raw: "NB-482791", token: "[CUSTOMER_ID_1]", type: "CUSTOMER_ID" }, { raw: "ABCDE1234F", token: "[TAX_ID_1]", type: "PAN" }] },
  { speaker: "Customer", role: "secondary", time: "00:22", raw: "The mobile linked to my account is +91 98765 43210.", safe: "The mobile linked to my account is [PHONE_1].", entities: [{ raw: "+91 98765 43210", token: "[PHONE_1]", type: "PHONE" }] },
  { speaker: "Agent", role: "primary", time: "00:31", raw: "I can help with the failed transfer. Please do not share your OTP or PIN.", safe: "I can help with the failed transfer. Please do not share your [OTP] or [PIN].", entities: [{ raw: "OTP", token: "[OTP]", type: "SECRET" }, { raw: "PIN", token: "[PIN]", type: "SECRET" }] },
  { speaker: "Customer", role: "secondary", time: "00:43", raw: "It was ₹45,000 to Neha Gupta, account 492188407721, IFSC HDFC0001234.", safe: "It was ₹45,000 to [BENEFICIARY_1], account [ACCOUNT_1], IFSC [IFSC_1].", entities: [{ raw: "Neha Gupta", token: "[BENEFICIARY_1]", type: "PERSON" }, { raw: "492188407721", token: "[ACCOUNT_1]", type: "ACCOUNT" }, { raw: "HDFC0001234", token: "[IFSC_1]", type: "IFSC" }] },
  { speaker: "Agent", role: "primary", time: "00:55", raw: "The transaction is pending, not lost. I have raised case FIN-883194.", safe: "The transaction is pending, not lost. I have raised case [CASE_ID_1].", entities: [{ raw: "FIN-883194", token: "[CASE_ID_1]", type: "CASE_ID" }] },
];

const insurance: TranscriptTurn[] = [
  { speaker: "Agent", role: "primary", time: "00:03", raw: "I’m Aditi Desai from the motor claims team. Please describe the incident.", safe: "I’m [AGENT_1] from the motor claims team. Please describe the incident.", entities: [{ raw: "Aditi Desai", token: "[AGENT_1]", type: "PERSON" }] },
  { speaker: "Policyholder", role: "secondary", time: "00:11", raw: "I’m Vikram Pillai. Policy number LC-MTR-884201 and vehicle KA03MX4821.", safe: "I’m [POLICYHOLDER_1]. Policy number [POLICY_ID_1] and vehicle [VEHICLE_ID_1].", entities: [{ raw: "Vikram Pillai", token: "[POLICYHOLDER_1]", type: "PERSON" }, { raw: "LC-MTR-884201", token: "[POLICY_ID_1]", type: "POLICY" }, { raw: "KA03MX4821", token: "[VEHICLE_ID_1]", type: "VEHICLE" }] },
  { speaker: "Policyholder", role: "secondary", time: "00:21", raw: "The accident happened near 18 Palm Grove Road, Indiranagar, at 8:30 PM.", safe: "The accident happened near [LOCATION_1], at [TIME_1].", entities: [{ raw: "18 Palm Grove Road, Indiranagar", token: "[LOCATION_1]", type: "ADDRESS" }, { raw: "8:30 PM", token: "[TIME_1]", type: "TIME" }] },
  { speaker: "Agent", role: "primary", time: "00:34", raw: "Was anyone injured, and was a police report filed?", safe: "Was anyone injured, and was a police report filed?", entities: [] },
  { speaker: "Witness", role: "unknown", time: "00:45", raw: "My name is Rakesh Jain and my phone is +91 99887 66554. I saw the collision.", safe: "My name is [WITNESS_1] and my phone is [PHONE_1]. I saw the collision.", entities: [{ raw: "Rakesh Jain", token: "[WITNESS_1]", type: "PERSON" }, { raw: "+91 99887 66554", token: "[PHONE_1]", type: "PHONE" }] },
  { speaker: "Agent", role: "primary", time: "00:57", raw: "Thank you. Claim reference CLM-572901 is now open for review.", safe: "Thank you. Claim reference [CLAIM_ID_1] is now open for review.", entities: [{ raw: "CLM-572901", token: "[CLAIM_ID_1]", type: "CLAIM" }] },
];

const bpo: TranscriptTurn[] = [
  { speaker: "Agent", role: "primary", time: "00:04", raw: "Thank you for calling Acme Mobile. I’m agent Rahul Verma.", safe: "Thank you for calling [COMPANY_1]. I’m [AGENT_1].", entities: [{ raw: "Acme Mobile", token: "[COMPANY_1]", type: "ORG" }, { raw: "Rahul Verma", token: "[AGENT_1]", type: "PERSON" }] },
  { speaker: "Customer", role: "secondary", time: "00:13", raw: "I’m Sana Chawla. My number is +91 98765 43210 and email sana.chawla@example.com.", safe: "I’m [CUSTOMER_1]. My number is [PHONE_1] and email [EMAIL_1].", entities: [{ raw: "Sana Chawla", token: "[CUSTOMER_1]", type: "PERSON" }, { raw: "+91 98765 43210", token: "[PHONE_1]", type: "PHONE" }, { raw: "sana.chawla@example.com", token: "[EMAIL_1]", type: "EMAIL" }] },
  { speaker: "Customer", role: "secondary", time: "00:25", raw: "My account 7744001288 was charged twice for ₹1,499.", safe: "My account [ACCOUNT_1] was charged twice for ₹1,499.", entities: [{ raw: "7744001288", token: "[ACCOUNT_1]", type: "ACCOUNT" }] },
  { speaker: "Agent", role: "primary", time: "00:36", raw: "I see the duplicate charge and can create a refund request.", safe: "I see the duplicate charge and can create a refund request.", entities: [] },
  { speaker: "Customer", role: "secondary", time: "00:46", raw: "Please send confirmation to 42 Lake View Avenue, Bengaluru.", safe: "Please send confirmation to [ADDRESS_1].", entities: [{ raw: "42 Lake View Avenue, Bengaluru", token: "[ADDRESS_1]", type: "ADDRESS" }] },
  { speaker: "Agent", role: "primary", time: "00:57", raw: "Request REF-119420 has been created. Expected resolution is three business days.", safe: "Request [CASE_ID_1] has been created. Expected resolution is three business days.", entities: [{ raw: "REF-119420", token: "[CASE_ID_1]", type: "CASE" }] },
];

const saas: TranscriptTurn[] = [
  { speaker: "Employee", role: "primary", time: "00:03", raw: "I’m Dev Patel from the platform team. Summarize this incident for Jira.", safe: "I’m [EMPLOYEE_1] from the platform team. Summarize this incident for Jira.", entities: [{ raw: "Dev Patel", token: "[EMPLOYEE_1]", type: "PERSON" }] },
  { speaker: "Customer", role: "secondary", time: "00:12", raw: "The affected tenant is Orion Labs, customer ID CUS-884201.", safe: "The affected tenant is [CUSTOMER_ORG_1], customer ID [CUSTOMER_ID_1].", entities: [{ raw: "Orion Labs", token: "[CUSTOMER_ORG_1]", type: "ORG" }, { raw: "CUS-884201", token: "[CUSTOMER_ID_1]", type: "CUSTOMER_ID" }] },
  { speaker: "Employee", role: "primary", time: "00:22", raw: "Logs show database host prod-db-07.internal and IP 10.24.8.19.", safe: "Logs show database host [HOST_1] and IP [IP_ADDRESS_1].", entities: [{ raw: "prod-db-07.internal", token: "[HOST_1]", type: "HOST" }, { raw: "10.24.8.19", token: "[IP_ADDRESS_1]", type: "IP" }] },
  { speaker: "Employee", role: "primary", time: "00:34", raw: "The API key pasted in chat starts sk_live_51M3q8x2 and must be revoked.", safe: "The API key pasted in chat starts [SECRET_1] and must be revoked.", entities: [{ raw: "sk_live_51M3q8x2", token: "[SECRET_1]", type: "SECRET" }] },
  { speaker: "Customer", role: "secondary", time: "00:45", raw: "Contact Mina Hall at mina.hall@orionlabs.com after the fix.", safe: "Contact [CUSTOMER_CONTACT_1] at [EMAIL_1] after the fix.", entities: [{ raw: "Mina Hall", token: "[CUSTOMER_CONTACT_1]", type: "PERSON" }, { raw: "mina.hall@orionlabs.com", token: "[EMAIL_1]", type: "EMAIL" }] },
  { speaker: "Employee", role: "primary", time: "00:56", raw: "Root cause was an expired certificate; no customer records were lost.", safe: "Root cause was an expired certificate; no customer records were lost.", entities: [] },
];

export const INDUSTRIES: Industry[] = ["Healthcare", "Finance", "Insurance", "BPO / Contact center", "SaaS / Copilot"];

export const DEMOS: Record<Industry, IndustryDemo> = {
  Healthcare: { industry: "Healthcare", policy: "Healthcare · HIPAA", route: "Clinical note AI", destination: "FHIR / EHR", speakers: [
    { initials: "AR", name: "Dr. Anika Rao", role: "Clinician", track: "SPEAKER_A", assurance: "SSO verified", status: "verified", color: "primary" },
    { initials: "AM", name: "Arjun Mehta", role: "Patient", track: "SPEAKER_B", assurance: "Check-in + OTP", status: "verified", color: "secondary" },
    { initials: "N", name: "Unknown", role: "Bystander", track: "SPEAKER_C", assurance: "No identity assertion", status: "unknown", color: "unknown" },
  ], transcript: healthcare },
  Finance: { industry: "Finance", policy: "Financial services · PCI", route: "Banking support AI", destination: "CRM / Core banking", speakers: [
    { initials: "RS", name: "Rhea Singh", role: "Bank agent", track: "SPEAKER_A", assurance: "SSO verified", status: "verified", color: "primary" },
    { initials: "KM", name: "Karan Malhotra", role: "Customer", track: "SPEAKER_B", assurance: "App OTP verified", status: "verified", color: "secondary" },
    { initials: "U", name: "Unknown", role: "Third party", track: "SPEAKER_C", assurance: "No identity assertion", status: "unknown", color: "unknown" },
  ], transcript: finance },
  Insurance: { industry: "Insurance", policy: "Insurance claims", route: "Claims summarization AI", destination: "Claims platform", speakers: [
    { initials: "AD", name: "Aditi Desai", role: "Claims agent", track: "SPEAKER_A", assurance: "SSO verified", status: "verified", color: "primary" },
    { initials: "VP", name: "Vikram Pillai", role: "Policyholder", track: "SPEAKER_B", assurance: "Policy OTP verified", status: "verified", color: "secondary" },
    { initials: "RJ", name: "Rakesh Jain", role: "Witness", track: "SPEAKER_C", assurance: "Claimed only", status: "claimed", color: "unknown" },
  ], transcript: insurance },
  "BPO / Contact center": { industry: "BPO / Contact center", policy: "Contact center privacy", route: "QA + agent assist AI", destination: "CRM / QA platform", speakers: [
    { initials: "A", name: "Agent 1042", role: "Support agent", track: "SPEAKER_A", assurance: "Workforce SSO", status: "verified", color: "primary" },
    { initials: "SC", name: "Sana Chawla", role: "Customer", track: "SPEAKER_B", assurance: "IVR OTP verified", status: "verified", color: "secondary" },
    { initials: "SV", name: "Supervisor", role: "Silent monitor", track: "SPEAKER_C", assurance: "SSO verified", status: "verified", color: "unknown" },
  ], transcript: bpo },
  "SaaS / Copilot": { industry: "SaaS / Copilot", policy: "Internal copilot DLP", route: "Enterprise copilot", destination: "Ticketing / knowledge base", speakers: [
    { initials: "DP", name: "Dev Patel", role: "Employee", track: "SPEAKER_A", assurance: "Corporate SSO", status: "verified", color: "primary" },
    { initials: "MH", name: "Mina Hall", role: "Customer", track: "SPEAKER_B", assurance: "CRM matched", status: "claimed", color: "secondary" },
    { initials: "U", name: "Unknown", role: "Meeting guest", track: "SPEAKER_C", assurance: "No identity assertion", status: "unknown", color: "unknown" },
  ], transcript: saas },
};

export const NAV_META = {
  overview: ["AI privacy operations", "Overview"], live: ["Real-time protection", "Live Shield"], policies: ["Governance", "Policy Studio"],
  vault: ["Trust plane", "Token Vault"], audit: ["Evidence", "Audit Trail"], connections: ["Platform", "Connections"],
  lab: ["Validation", "Performance Lab"], settings: ["Workspace", "Settings"],
} as const;
