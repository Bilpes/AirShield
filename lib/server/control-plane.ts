import { readFile } from "node:fs/promises";

const explicitDevelopmentRuntime =
  process.env.AIRSHIELD_RUNTIME_MODE === "development" &&
  process.env.AIRSHIELD_ALLOW_DEVELOPMENT_RUNTIME === "true";
export const productionMode =
  process.env.AIRSHIELD_RUNTIME_MODE === "production" ||
  (process.env.NODE_ENV === "production" && !explicitDevelopmentRuntime);

function requireHttpsInProduction(name: "CONTROL_PLANE_URL" | "OLLAMA_BASE_URL"): void {
  const value = process.env[name];
  if (!productionMode || !value) return;
  try {
    if (new URL(value).protocol !== "https:") throw new Error();
  } catch {
    throw new Error(`${name} must be an absolute HTTPS URL in production`);
  }
}

requireHttpsInProduction("CONTROL_PLANE_URL");
requireHttpsInProduction("OLLAMA_BASE_URL");

const policyAliases: Record<string, string> = {
  "Healthcare · HIPAA": "healthcare-us-eu-v1",
  "Financial services · PCI": "finance-eu-us-v1",
  "Insurance claims": "insurance-eu-us-v1",
  "Contact center privacy": "contact-center-eu-us-v1",
  "Internal copilot DLP": "saas-copilot-eu-us-v1",
};

const destinationAliases: Record<string, string> = {
  "Clinical note AI": "approved-health-llm",
  "Banking support AI": "approved-finance-llm",
  "Claims summarization AI": "approved-insurance-llm",
  "QA + agent assist AI": "approved-contact-center-llm",
  "Enterprise copilot": "enterprise-copilot",
};

export function controlPolicy(value: unknown): string {
  const supplied = typeof value === "string" ? value : "";
  return policyAliases[supplied] ?? supplied;
}

export function controlDestination(_policy: string, value: unknown): string {
  const supplied = typeof value === "string" ? value : "";
  return destinationAliases[supplied] ?? supplied;
}

let cachedAccessToken: { token: string; expiresAt: number } | undefined;

function required(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`${name} is required`);
  return value;
}

async function workloadToken(): Promise<string> {
  if (cachedAccessToken && cachedAccessToken.expiresAt > Date.now() + 60_000) {
    return cachedAccessToken.token;
  }

  const federatedTokenFile = process.env.AZURE_FEDERATED_TOKEN_FILE;
  if (federatedTokenFile) {
    const tenant = required("AZURE_TENANT_ID");
    const clientId = required("AZURE_CLIENT_ID");
    const assertion = (await readFile(federatedTokenFile, "utf8")).trim();
    const form = new URLSearchParams({
      client_id: clientId,
      scope: required("CONTROL_PLANE_SCOPE"),
      grant_type: "client_credentials",
      client_assertion_type: "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
      client_assertion: assertion,
    });
    const response = await fetch(
      `https://login.microsoftonline.com/${encodeURIComponent(tenant)}/oauth2/v2.0/token`,
      { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body: form },
    );
    if (!response.ok) throw new Error(`Workload identity exchange failed (${response.status})`);
    const result = (await response.json()) as { access_token?: string; expires_in?: number };
    if (!result.access_token) throw new Error("Workload identity exchange returned no access token");
    cachedAccessToken = {
      token: result.access_token,
      expiresAt: Date.now() + Math.max(60, result.expires_in ?? 300) * 1000,
    };
    return result.access_token;
  }

  const directTokenFile = process.env.CONTROL_PLANE_TOKEN_FILE;
  if (directTokenFile) return (await readFile(directTokenFile, "utf8")).trim();

  if (!productionMode) return process.env.CONTROL_PLANE_DEV_TOKEN || "development-only";
  throw new Error("No workload identity token source is configured");
}

export function controlPlaneConfigured(): boolean {
  return Boolean(process.env.CONTROL_PLANE_URL);
}

export async function controlPlaneFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const base = required("CONTROL_PLANE_URL").replace(/\/$/, "");
  const token = await workloadToken();
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${token}`);
  headers.set("Accept", "application/json");
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  return fetch(`${base}${path}`, { ...init, headers, cache: "no-store", signal: init.signal ?? AbortSignal.timeout(20_000) });
}

export async function createControlSession(policy: string): Promise<string> {
  const response = await controlPlaneFetch("/v1/sessions", {
    method: "POST",
    body: JSON.stringify({ policy, language: "en", ttl_minutes: 60 }),
  });
  if (!response.ok) throw new Error(`Control-plane session failed (${response.status})`);
  const data = (await response.json()) as { session_id?: string };
  if (!data.session_id) throw new Error("Control-plane session returned no identifier");
  return data.session_id;
}
