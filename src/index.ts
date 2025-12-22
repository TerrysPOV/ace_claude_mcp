/**
 * ACE (Agentic Context Engineering) MCP Server for Cloudflare Workers
 *
 * Provides MCP tools for managing evolving playbooks with D1 database backend.
 * Supports multi-project playbooks with global + project-specific entries.
 *
 * Dual transport support:
 * - /sse - Legacy SSE transport (Claude Code, Claude Desktop)
 * - /mcp - Streamable HTTP transport (OpenAI ChatGPT, Codex CLI)
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { WebStandardStreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/webStandardStreamableHttp.js";
import { isInitializeRequest } from "@modelcontextprotocol/sdk/types.js";
import { McpAgent } from "agents/mcp";
import { z } from "zod";

interface Env {
  DB: D1Database;
  MCP_AGENT: DurableObjectNamespace<AceMcpAgent>;
  DEFAULT_USER_ID?: string;
  REQUIRE_AUTH?: string;
  OAUTH_CLIENT_ID?: string;
  OAUTH_CLIENT_SECRET?: string;
  OAUTH_REDIRECT_URIS?: string;
  GOOGLE_CLIENT_ID?: string;
  GOOGLE_CLIENT_SECRET?: string;
  GOOGLE_REDIRECT_URI?: string;
  JWT_SECRET?: string;
}

type PlaybookEntry = {
  entry_id: string;
  project_id: string;
  user_id: string;
  section: string;
  content: string;
  helpful_count: number;
  harmful_count: number;
};

type ProjectRecord = {
  project_id: string;
  description?: string | null;
};

type StreamableSession = {
  server: McpServer;
  transport: WebStandardStreamableHTTPServerTransport;
  userId: string;
};

type AuthInfo = {
  userId: string;
  email?: string;
};

// Section prefixes for ID generation
const SECTION_PREFIXES: Record<string, string> = {
  "STRATEGIES & INSIGHTS": "str",
  "FORMULAS & CALCULATIONS": "cal",
  "COMMON MISTAKES TO AVOID": "mis",
  "DOMAIN KNOWLEDGE": "dom",
};

const VALID_SECTIONS = Object.keys(SECTION_PREFIXES);

// Generate unique entry ID
function generateEntryId(section: string): string {
  const prefix = SECTION_PREFIXES[section] || "unk";
  const num = String(Math.floor(Math.random() * 100000)).padStart(5, "0");
  return `${prefix}-${num}`;
}

// Format entry for display
function formatEntry(entry: PlaybookEntry): string {
  return `[${entry.entry_id}] helpful=${entry.helpful_count} harmful=${entry.harmful_count} :: ${entry.content}`;
}

const TEXT_ENCODER = new TextEncoder();
const TEXT_DECODER = new TextDecoder();

const DEFAULT_ENTRIES: Array<{ entry_id: string; section: string; content: string }> = [
  {
    entry_id: "str-00001",
    section: "STRATEGIES & INSIGHTS",
    content: "Break complex problems into smaller, manageable steps.",
  },
  {
    entry_id: "str-00002",
    section: "STRATEGIES & INSIGHTS",
    content: "Validate assumptions before proceeding with solutions.",
  },
  {
    entry_id: "cal-00001",
    section: "FORMULAS & CALCULATIONS",
    content: "ROI = (Gain - Cost) / Cost * 100",
  },
  {
    entry_id: "mis-00001",
    section: "COMMON MISTAKES TO AVOID",
    content: "Don't assume input data is clean - always validate.",
  },
  {
    entry_id: "dom-00001",
    section: "DOMAIN KNOWLEDGE",
    content: "Context window limits require prioritizing relevant information.",
  },
];

function base64UrlEncode(data: ArrayBuffer): string {
  const bytes = new Uint8Array(data);
  let binary = "";
  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function base64UrlDecode(input: string): Uint8Array {
  const padded = input.replace(/-/g, "+").replace(/_/g, "/") + "===".slice((input.length + 3) % 4);
  const binary = atob(padded);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

async function hmacSha256(secret: string, data: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    TEXT_ENCODER.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const signature = await crypto.subtle.sign("HMAC", key, TEXT_ENCODER.encode(data));
  return base64UrlEncode(signature);
}

async function sha256Base64Url(data: string): Promise<string> {
  const hash = await crypto.subtle.digest("SHA-256", TEXT_ENCODER.encode(data));
  return base64UrlEncode(hash);
}

function timingSafeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) {
    return false;
  }
  let result = 0;
  for (let i = 0; i < a.length; i += 1) {
    result |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return result === 0;
}

async function signJwt(payload: Record<string, unknown>, secret: string): Promise<string> {
  const header = { alg: "HS256", typ: "JWT" };
  const headerPart = base64UrlEncode(TEXT_ENCODER.encode(JSON.stringify(header)));
  const payloadPart = base64UrlEncode(TEXT_ENCODER.encode(JSON.stringify(payload)));
  const signingInput = `${headerPart}.${payloadPart}`;
  const signature = await hmacSha256(secret, signingInput);
  return `${signingInput}.${signature}`;
}

async function verifyJwt(token: string, secret: string): Promise<Record<string, unknown> | null> {
  const parts = token.split(".");
  if (parts.length !== 3) {
    return null;
  }
  const [headerPart, payloadPart, signature] = parts;
  const expectedSignature = await hmacSha256(secret, `${headerPart}.${payloadPart}`);
  if (!timingSafeEqual(signature, expectedSignature)) {
    return null;
  }
  const payloadBytes = base64UrlDecode(payloadPart);
  const payloadJson = TEXT_DECODER.decode(payloadBytes);
  try {
    return JSON.parse(payloadJson) as Record<string, unknown>;
  } catch {
    return null;
  }
}

function getEnvBool(envValue: string | undefined, defaultValue: boolean): boolean {
  if (envValue === undefined) {
    return defaultValue;
  }
  return envValue.toLowerCase() === "true";
}

function resolveUserId(extra: { authInfo?: AuthInfo } | undefined, env: Env): string {
  if (extra?.authInfo?.userId) {
    return extra.authInfo.userId;
  }
  if (env.DEFAULT_USER_ID) {
    return env.DEFAULT_USER_ID;
  }
  throw new Error("Unauthorized: missing user identity");
}

async function ensureUserSeeded(env: Env, userId: string): Promise<void> {
  const existing = await env.DB.prepare(
    `SELECT project_id FROM projects WHERE user_id = ? AND project_id = 'global'`
  )
    .bind(userId)
    .first<{ project_id: string }>();
  if (existing) {
    return;
  }

  await env.DB.prepare(`
    INSERT INTO projects (project_id, user_id, description, created_at)
    VALUES ('global', ?, 'Universal patterns and insights shared across all projects', datetime('now'))
  `)
    .bind(userId)
    .run();

  const insert = env.DB.prepare(`
    INSERT INTO entries (entry_id, project_id, user_id, section, content, helpful_count, harmful_count)
    VALUES (?, 'global', ?, ?, ?, 0, 0)
  `);
  for (const entry of DEFAULT_ENTRIES) {
    await insert.bind(entry.entry_id, userId, entry.section, entry.content).run();
  }
}

function registerPlaybookTools(server: McpServer, envProvider: () => Env): void {
  const getUserContext = async (extra?: { authInfo?: AuthInfo }) => {
    const env = envProvider();
    const userId = resolveUserId(extra, env);
    await ensureUserSeeded(env, userId);
    return { env, userId };
  };

  // Tool: read_playbook
  server.tool(
    "read_playbook",
    "Load the current playbook for a project. Merges global entries with project-specific entries.",
    { project_id: z.string().optional().describe("Project ID (defaults to 'global')") },
    async ({ project_id = "global" }, extra) => {
      const { env, userId } = await getUserContext(extra);
      const entries = await env.DB.prepare(`
        SELECT * FROM entries 
        WHERE user_id = ? AND (project_id = ? OR project_id = 'global')
        ORDER BY section, helpful_count DESC
      `)
        .bind(userId, project_id)
        .all<PlaybookEntry>();

      if (!entries.results?.length) {
        return {
          content: [{ type: "text", text: `No entries found for project '${project_id}'.` }],
        };
      }

      const bySection: Record<string, string[]> = {};
      for (const entry of entries.results) {
        const section = entry.section;
        if (!bySection[section]) {
          bySection[section] = [];
        }
        bySection[section].push(formatEntry(entry));
      }

      let output = `# ACE Playbook: ${project_id}\n\n`;
      for (const section of VALID_SECTIONS) {
        if (bySection[section]?.length) {
          output += `## ${section}\n`;
          output += `${bySection[section].join("\n")}\n\n`;
        }
      }

      return { content: [{ type: "text", text: output }] };
    }
  );

  // Tool: get_section
  server.tool(
    "get_section",
    "Get entries from a specific section of the playbook.",
    {
      section: z.enum(VALID_SECTIONS as [string, ...string[]]).describe("Section name"),
      project_id: z.string().optional().describe("Project ID (defaults to 'global')"),
    },
    async ({ section, project_id = "global" }, extra) => {
      const { env, userId } = await getUserContext(extra);
      const entries = await env.DB.prepare(`
        SELECT * FROM entries 
        WHERE user_id = ? AND section = ? AND (project_id = ? OR project_id = 'global')
        ORDER BY helpful_count DESC
      `)
        .bind(userId, section, project_id)
        .all<PlaybookEntry>();

      if (!entries.results?.length) {
        return {
          content: [
            { type: "text", text: `No entries in '${section}' for project '${project_id}'.` },
          ],
        };
      }

      const formatted = entries.results.map(formatEntry).join("\n");
      return {
        content: [
          {
            type: "text",
            text: `## ${section}
${formatted}`,
          },
        ],
      };
    }
  );

  // Tool: add_entry
  server.tool(
    "add_entry",
    "Add a new entry to the playbook. Use for strategies, domain knowledge, mistakes, or formulas.",
    {
      section: z.enum(VALID_SECTIONS as [string, ...string[]]).describe("Section to add entry to"),
      content: z.string().describe("The insight or knowledge to save"),
      project_id: z.string().optional().describe("Project ID (defaults to 'global')"),
    },
    async ({ section, content, project_id = "global" }, extra) => {
      const { env, userId } = await getUserContext(extra);
      const entry_id = generateEntryId(section);
      await env.DB.prepare(`
        INSERT INTO entries (entry_id, project_id, user_id, section, content, helpful_count, harmful_count)
        VALUES (?, ?, ?, ?, ?, 0, 0)
      `)
        .bind(entry_id, project_id, userId, section, content)
        .run();

      return {
        content: [
          { type: "text", text: `Added [${entry_id}] to ${section} (project: ${project_id})` },
        ],
      };
    }
  );

  // Tool: update_counters
  server.tool(
    "update_counters",
    "Update the helpful/harmful counters for an entry based on its effectiveness.",
    {
      entry_id: z.string().describe("Entry ID (e.g., 'str-00001')"),
      helpful_delta: z.number().optional().describe("Amount to add to helpful count"),
      harmful_delta: z.number().optional().describe("Amount to add to harmful count"),
    },
    async ({ entry_id, helpful_delta = 0, harmful_delta = 0 }, extra) => {
      const { env, userId } = await getUserContext(extra);
      const result = await env.DB.prepare(`
        UPDATE entries 
        SET helpful_count = helpful_count + ?, harmful_count = harmful_count + ?
        WHERE entry_id = ? AND user_id = ?
      `)
        .bind(helpful_delta, harmful_delta, entry_id, userId)
        .run();

      if (result.meta.changes === 0) {
        return { content: [{ type: "text", text: `Entry '${entry_id}' not found.` }] };
      }

      return {
        content: [
          {
            type: "text",
            text: `Updated ${entry_id}: helpful +${helpful_delta}, harmful +${harmful_delta}`,
          },
        ],
      };
    }
  );

  // Tool: remove_entry
  server.tool(
    "remove_entry",
    "Remove an entry from the playbook.",
    { entry_id: z.string().describe("Entry ID to remove") },
    async ({ entry_id }, extra) => {
      const { env, userId } = await getUserContext(extra);
      const result = await env.DB.prepare("DELETE FROM entries WHERE entry_id = ? AND user_id = ?")
        .bind(entry_id, userId)
        .run();
      if (result.meta.changes === 0) {
        return { content: [{ type: "text", text: `Entry '${entry_id}' not found.` }] };
      }
      return { content: [{ type: "text", text: `Removed entry '${entry_id}'.` }] };
    }
  );

  // Tool: log_reflection
  server.tool(
    "log_reflection",
    "Log a reflection about a task outcome for future learning.",
    {
      task_summary: z.string().describe("Brief description of the task"),
      outcome: z.enum(["success", "partial", "failure"]).describe("Task outcome"),
      learnings: z.string().describe("Key learnings or insights from this task"),
      project_id: z.string().optional().describe("Project ID (defaults to 'global')"),
    },
    async ({ task_summary, outcome, learnings, project_id = "global" }, extra) => {
      const { env, userId } = await getUserContext(extra);
      await env.DB.prepare(`
        INSERT INTO reflections (project_id, user_id, task_summary, outcome, learnings, created_at)
        VALUES (?, ?, ?, ?, ?, datetime('now'))
      `)
        .bind(project_id, userId, task_summary, outcome, learnings)
        .run();

      return {
        content: [{ type: "text", text: `Logged reflection for '${task_summary}' (${outcome}).` }],
      };
    }
  );

  // Tool: curate_playbook
  server.tool(
    "curate_playbook",
    "Remove low-quality entries (high harmful count relative to helpful).",
    {
      project_id: z.string().optional().describe("Project ID to curate"),
      harmful_threshold: z
        .number()
        .optional()
        .describe("Remove entries with harmful >= this (default: 3)"),
    },
    async ({ project_id, harmful_threshold = 3 }, extra) => {
      const { env, userId } = await getUserContext(extra);
      let query =
        "DELETE FROM entries WHERE user_id = ? AND harmful_count >= ? AND harmful_count > helpful_count";
      const params: Array<string | number> = [userId, harmful_threshold];

      if (project_id) {
        query += " AND project_id = ?";
        params.push(project_id);
      }

      const result = await env.DB.prepare(query)
        .bind(...params)
        .run();
      return {
        content: [
          {
            type: "text",
            text: `Curated playbook: removed ${result.meta.changes} low-quality entries.`,
          },
        ],
      };
    }
  );

  // Tool: search_playbook
  server.tool(
    "search_playbook",
    "Search for entries matching a query.",
    {
      query: z.string().describe("Search query"),
      project_id: z.string().optional().describe("Project ID to search (also searches global)"),
    },
    async ({ query, project_id = "global" }, extra) => {
      const { env, userId } = await getUserContext(extra);
      const entries = await env.DB.prepare(`
        SELECT * FROM entries 
        WHERE user_id = ? AND (project_id = ? OR project_id = 'global')
          AND content LIKE ?
        ORDER BY helpful_count DESC
        LIMIT 10
      `)
        .bind(userId, project_id, `%${query}%`)
        .all<PlaybookEntry>();

      if (!entries.results?.length) {
        return { content: [{ type: "text", text: `No entries matching '${query}'.` }] };
      }

      const formatted = entries.results.map(formatEntry).join("\n");
      return { content: [{ type: "text", text: `## Search Results: "${query}"\n${formatted}` }] };
    }
  );

  // Tool: list_projects
  server.tool("list_projects", "List all available projects.", {}, async (_, extra) => {
    const { env, userId } = await getUserContext(extra);
    const projects = await env.DB.prepare(
      "SELECT * FROM projects WHERE user_id = ? ORDER BY project_id"
    )
      .bind(userId)
      .all<ProjectRecord>();

    if (!projects.results?.length) {
      return {
        content: [{ type: "text", text: "No projects found. Use create_project to create one." }],
      };
    }

    const formatted = projects.results
      .map(
        (project) =>
          `- ${project.project_id}${project.description ? `: ${project.description}` : ""}`
      )
      .join("\n");

    return {
      content: [
        {
          type: "text",
          text: `## Projects
${formatted}`,
        },
      ],
    };
  });

  // Tool: create_project
  server.tool(
    "create_project",
    "Create a new project for organizing playbook entries.",
    {
      project_id: z.string().describe("Unique project identifier"),
      description: z.string().optional().describe("Project description"),
    },
    async ({ project_id, description }, extra) => {
      const { env, userId } = await getUserContext(extra);
      try {
        await env.DB.prepare(`
          INSERT INTO projects (project_id, user_id, description, created_at)
          VALUES (?, ?, ?, datetime('now'))
        `)
          .bind(project_id, userId, description || null)
          .run();
        return {
          content: [
            {
              type: "text",
              text: `Created project '${project_id}'${description ? `: ${description}` : ""}`,
            },
          ],
        };
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        if (message.includes("UNIQUE constraint")) {
          return { content: [{ type: "text", text: `Project '${project_id}' already exists.` }] };
        }
        throw error;
      }
    }
  );
}

// The Durable Object that handles MCP connections
export class AceMcpAgent extends McpAgent<Env> {
  server = new McpServer({
    name: "ace-playbook",
    version: "2.0.0",
  });

  async init() {
    registerPlaybookTools(this.server, () => this.env);
  }
}

function createStreamableServer(env: Env): McpServer {
  const server = new McpServer({
    name: "ace-playbook",
    version: "2.0.0",
  });
  registerPlaybookTools(server, () => env);
  return server;
}

function ensureAcceptHeader(request: Request): Request {
  const headers = new Headers(request.headers);
  const accept = headers.get("accept") || "";
  if (!accept.includes("application/json") || !accept.includes("text/event-stream")) {
    headers.set("accept", "application/json, text/event-stream");
  }
  return new Request(request, { headers });
}

async function parseJsonBody(request: Request): Promise<unknown | undefined> {
  if (request.method !== "POST") {
    return undefined;
  }
  const contentType = request.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    return undefined;
  }
  try {
    return await request.clone().json();
  } catch {
    return undefined;
  }
}

function isInitializePayload(payload: unknown): boolean {
  if (!payload) {
    return false;
  }
  if (Array.isArray(payload)) {
    return payload.some((message) => isInitializeRequest(message));
  }
  return isInitializeRequest(payload);
}

function jsonRpcError(status: number, message: string): Response {
  return new Response(
    JSON.stringify({
      jsonrpc: "2.0",
      error: { code: -32000, message },
      id: null,
    }),
    {
      status,
      headers: { "Content-Type": "application/json" },
    }
  );
}

async function getAuthInfo(request: Request, env: Env): Promise<AuthInfo | null> {
  const authHeader =
    request.headers.get("authorization") || request.headers.get("Authorization") || "";
  if (!authHeader.startsWith("Bearer ")) {
    return null;
  }
  const token = authHeader.slice("Bearer ".length).trim();
  if (!token || !env.JWT_SECRET) {
    return null;
  }
  const payload = await verifyJwt(token, env.JWT_SECRET);
  if (!payload) {
    return null;
  }
  const userId = payload.sub;
  if (typeof userId !== "string" || userId.length === 0) {
    return null;
  }
  const exp = payload.exp;
  if (typeof exp === "number" && exp * 1000 < Date.now()) {
    return null;
  }
  const email = typeof payload.email === "string" ? payload.email : undefined;
  return { userId, email };
}

const OAUTH_CODE_TTL_SECONDS = 300;
const ACCESS_TOKEN_TTL_SECONDS = 3600;
const REFRESH_TOKEN_TTL_SECONDS = 60 * 60 * 24 * 30;
const GOOGLE_SCOPES = "openid email profile";

function getAllowedRedirectUris(env: Env): string[] {
  return (env.OAUTH_REDIRECT_URIS || "")
    .split(",")
    .map((uri) => uri.trim())
    .filter(Boolean);
}

function oauthError(status: number, error: string, description: string): Response {
  return new Response(JSON.stringify({ error, error_description: description }), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function redirectWithParams(base: string, params: Record<string, string>): Response {
  const url = new URL(base);
  for (const [key, value] of Object.entries(params)) {
    url.searchParams.set(key, value);
  }
  return Response.redirect(url.toString(), 302);
}

async function buildOAuthState(env: Env, payload: Record<string, unknown>): Promise<string> {
  if (!env.JWT_SECRET) {
    throw new Error("Missing JWT_SECRET");
  }
  return signJwt(payload, env.JWT_SECRET);
}

async function verifyOAuthState(env: Env, token: string): Promise<Record<string, unknown> | null> {
  if (!env.JWT_SECRET) {
    return null;
  }
  const payload = await verifyJwt(token, env.JWT_SECRET);
  if (!payload) {
    return null;
  }
  const exp = payload.exp;
  if (typeof exp === "number" && exp * 1000 < Date.now()) {
    return null;
  }
  return payload;
}

async function handleOAuthAuthorize(request: Request, env: Env): Promise<Response> {
  const url = new URL(request.url);
  const responseType = url.searchParams.get("response_type");
  const clientId = url.searchParams.get("client_id") || "";
  const redirectUri = url.searchParams.get("redirect_uri") || "";
  const state = url.searchParams.get("state") || "";
  const codeChallenge = url.searchParams.get("code_challenge") || "";
  const codeChallengeMethod = url.searchParams.get("code_challenge_method") || "S256";

  if (responseType !== "code") {
    return oauthError(400, "unsupported_response_type", "response_type must be code");
  }
  let allowedRedirects: string[] = [];
  if (env.OAUTH_CLIENT_ID && clientId === env.OAUTH_CLIENT_ID) {
    allowedRedirects = getAllowedRedirectUris(env);
  } else {
    const record = await getClientRecord(env, clientId);
    if (!record) {
      return oauthError(400, "invalid_client", "Unknown client_id");
    }
    try {
      allowedRedirects = normalizeRedirectUris(JSON.parse(record.redirect_uris) as string[]);
    } catch {
      allowedRedirects = [];
    }
  }
  if (!allowedRedirects.includes(redirectUri)) {
    console.log("OAuth redirect_uri not allowlisted:", redirectUri);
    return oauthError(400, "invalid_request", "redirect_uri is not allowed");
  }
  if (!codeChallenge) {
    return oauthError(400, "invalid_request", "code_challenge is required");
  }
  if (codeChallengeMethod !== "S256" && codeChallengeMethod !== "plain") {
    return oauthError(400, "invalid_request", "Unsupported code_challenge_method");
  }
  if (!env.GOOGLE_CLIENT_ID || !env.GOOGLE_REDIRECT_URI) {
    return oauthError(500, "server_error", "Google OAuth is not configured");
  }

  const now = Math.floor(Date.now() / 1000);
  const signedState = await buildOAuthState(env, {
    client_id: clientId,
    redirect_uri: redirectUri,
    code_challenge: codeChallenge,
    code_challenge_method: codeChallengeMethod,
    state,
    iat: now,
    exp: now + OAUTH_CODE_TTL_SECONDS,
    nonce: crypto.randomUUID(),
  });

  const googleUrl = new URL("https://accounts.google.com/o/oauth2/v2/auth");
  googleUrl.searchParams.set("client_id", env.GOOGLE_CLIENT_ID);
  googleUrl.searchParams.set("redirect_uri", env.GOOGLE_REDIRECT_URI);
  googleUrl.searchParams.set("response_type", "code");
  googleUrl.searchParams.set("scope", GOOGLE_SCOPES);
  googleUrl.searchParams.set("state", signedState);
  googleUrl.searchParams.set("access_type", "offline");
  googleUrl.searchParams.set("prompt", "consent");

  return Response.redirect(googleUrl.toString(), 302);
}

async function handleOAuthRegister(request: Request, env: Env): Promise<Response> {
  if (request.method !== "POST") {
    return new Response("Method Not Allowed", { status: 405 });
  }
  let payload: { redirect_uris?: string[]; client_name?: string } = {};
  try {
    payload = (await request.json()) as { redirect_uris?: string[]; client_name?: string };
  } catch {
    return oauthError(400, "invalid_request", "Invalid JSON payload");
  }
  const redirectUris = normalizeRedirectUris(payload.redirect_uris ?? null);
  if (redirectUris.length === 0) {
    return oauthError(400, "invalid_request", "redirect_uris is required");
  }
  const clientId = crypto.randomUUID().replace(/-/g, "");
  const clientSecret = base64UrlEncode(crypto.getRandomValues(new Uint8Array(32)).buffer);
  const secretHash = await sha256Base64Url(clientSecret);

  await env.DB.prepare(`
    INSERT INTO oauth_clients (client_id, client_secret_hash, redirect_uris, created_at)
    VALUES (?, ?, ?, datetime('now'))
  `)
    .bind(clientId, secretHash, JSON.stringify(redirectUris))
    .run();

  const issuer = buildIssuer(request);
  return jsonResponse({
    client_id: clientId,
    client_secret: clientSecret,
    client_name: payload.client_name,
    redirect_uris: redirectUris,
    token_endpoint_auth_method: "client_secret_post",
    grant_types: ["authorization_code", "refresh_token"],
    response_types: ["code"],
    application_type: "web",
    client_id_issued_at: Math.floor(Date.now() / 1000),
    client_secret_expires_at: 0,
    registration_client_uri: `${issuer}/oauth/register/${clientId}`,
  });
}

async function exchangeGoogleCode(
  env: Env,
  code: string
): Promise<{ sub: string; email?: string }> {
  if (!env.GOOGLE_CLIENT_ID || !env.GOOGLE_CLIENT_SECRET || !env.GOOGLE_REDIRECT_URI) {
    throw new Error("Google OAuth not configured");
  }
  const tokenBody = new URLSearchParams({
    code,
    client_id: env.GOOGLE_CLIENT_ID,
    client_secret: env.GOOGLE_CLIENT_SECRET,
    redirect_uri: env.GOOGLE_REDIRECT_URI,
    grant_type: "authorization_code",
  });

  const tokenResp = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: tokenBody.toString(),
  });
  if (!tokenResp.ok) {
    throw new Error("Failed to exchange Google code");
  }
  const tokenJson = (await tokenResp.json()) as { access_token?: string };
  if (!tokenJson.access_token) {
    throw new Error("Missing Google access token");
  }

  const userResp = await fetch("https://openidconnect.googleapis.com/v1/userinfo", {
    headers: { Authorization: `Bearer ${tokenJson.access_token}` },
  });
  if (!userResp.ok) {
    throw new Error("Failed to fetch Google userinfo");
  }
  const userJson = (await userResp.json()) as { sub?: string; email?: string };
  if (!userJson.sub) {
    throw new Error("Missing Google subject");
  }
  return { sub: userJson.sub, email: userJson.email };
}

async function handleOAuthCallback(request: Request, env: Env): Promise<Response> {
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const stateToken = url.searchParams.get("state") || "";
  if (!code || !stateToken) {
    return new Response("Missing code or state", { status: 400 });
  }

  const statePayload = await verifyOAuthState(env, stateToken);
  if (!statePayload) {
    return new Response("Invalid state", { status: 400 });
  }

  const clientId = typeof statePayload.client_id === "string" ? statePayload.client_id : "";
  const redirectUri =
    typeof statePayload.redirect_uri === "string" ? statePayload.redirect_uri : "";
  const originalState = typeof statePayload.state === "string" ? statePayload.state : "";
  const codeChallenge =
    typeof statePayload.code_challenge === "string" ? statePayload.code_challenge : "";
  const codeChallengeMethod =
    typeof statePayload.code_challenge_method === "string"
      ? statePayload.code_challenge_method
      : "S256";

  if (!clientId || !redirectUri) {
    return new Response("Invalid state payload", { status: 400 });
  }

  let userInfo: { sub: string; email?: string };
  try {
    userInfo = await exchangeGoogleCode(env, code);
  } catch (error) {
    return new Response(String(error), { status: 400 });
  }

  await env.DB.prepare(`
    INSERT OR IGNORE INTO users (user_id, google_sub, email, created_at)
    VALUES (?, ?, ?, datetime('now'))
  `)
    .bind(userInfo.sub, userInfo.sub, userInfo.email || null)
    .run();

  const authCode = crypto.randomUUID();
  await env.DB.prepare(`
    INSERT INTO oauth_codes (code, client_id, redirect_uri, user_id, code_challenge, code_challenge_method, expires_at)
    VALUES (?, ?, ?, ?, ?, ?, datetime('now', '+${OAUTH_CODE_TTL_SECONDS} seconds'))
  `)
    .bind(authCode, clientId, redirectUri, userInfo.sub, codeChallenge, codeChallengeMethod)
    .run();

  const redirectParams: Record<string, string> = { code: authCode };
  if (originalState) {
    redirectParams.state = originalState;
  }
  return redirectWithParams(redirectUri, redirectParams);
}

async function handleOAuthToken(request: Request, env: Env): Promise<Response> {
  const body = await request.text();
  const params = new URLSearchParams(body);
  const grantType = params.get("grant_type");
  const clientId = params.get("client_id") || "";
  const clientSecret = params.get("client_secret") || "";
  const redirectUri = params.get("redirect_uri") || "";

  if (!clientId || !clientSecret) {
    return oauthError(401, "invalid_client", "Missing client credentials");
  }
  const verifiedClient = await verifyClientCredentials(env, clientId, clientSecret);
  if (!verifiedClient) {
    return oauthError(401, "invalid_client", "Invalid client credentials");
  }

  if (grantType === "authorization_code") {
    const code = params.get("code") || "";
    const codeVerifier = params.get("code_verifier") || "";
    if (!code || !redirectUri) {
      return oauthError(400, "invalid_request", "Missing code or redirect_uri");
    }
    const row = await env.DB.prepare(`
      SELECT code, client_id, redirect_uri, user_id, code_challenge, code_challenge_method, expires_at
      FROM oauth_codes
      WHERE code = ?
    `)
      .bind(code)
      .first<{
        client_id: string;
        redirect_uri: string;
        user_id: string;
        code_challenge: string;
        code_challenge_method: string;
        expires_at: string;
      }>();
    if (!row) {
      return oauthError(400, "invalid_grant", "Invalid authorization code");
    }
    if (row.client_id !== clientId || row.redirect_uri !== redirectUri) {
      return oauthError(400, "invalid_grant", "Authorization code mismatch");
    }
    if (row.expires_at && Date.parse(row.expires_at) < Date.now()) {
      return oauthError(400, "invalid_grant", "Authorization code expired");
    }
    if (!codeVerifier) {
      return oauthError(400, "invalid_request", "Missing code_verifier");
    }
    if (row.code_challenge_method === "S256") {
      const computed = await sha256Base64Url(codeVerifier);
      if (!timingSafeEqual(computed, row.code_challenge)) {
        return oauthError(400, "invalid_grant", "Invalid code_verifier");
      }
    } else if (row.code_challenge_method === "plain") {
      if (!timingSafeEqual(codeVerifier, row.code_challenge)) {
        return oauthError(400, "invalid_grant", "Invalid code_verifier");
      }
    } else {
      return oauthError(400, "invalid_request", "Unsupported code_challenge_method");
    }

    await env.DB.prepare("DELETE FROM oauth_codes WHERE code = ?").bind(code).run();

    if (!env.JWT_SECRET) {
      return oauthError(500, "server_error", "JWT secret not configured");
    }
    const now = Math.floor(Date.now() / 1000);
    const accessToken = await signJwt(
      {
        sub: row.user_id,
        iat: now,
        exp: now + ACCESS_TOKEN_TTL_SECONDS,
        scope: "mcp",
      },
      env.JWT_SECRET
    );

    const refreshToken = base64UrlEncode(crypto.getRandomValues(new Uint8Array(32)).buffer);
    const refreshHash = await sha256Base64Url(refreshToken);
    await env.DB.prepare(`
      INSERT INTO oauth_refresh_tokens (token_hash, user_id, client_id, expires_at, created_at)
      VALUES (?, ?, ?, datetime('now', '+${REFRESH_TOKEN_TTL_SECONDS} seconds'), datetime('now'))
    `)
      .bind(refreshHash, row.user_id, clientId)
      .run();

    return new Response(
      JSON.stringify({
        access_token: accessToken,
        token_type: "Bearer",
        expires_in: ACCESS_TOKEN_TTL_SECONDS,
        refresh_token: refreshToken,
        scope: "mcp",
      }),
      { headers: { "Content-Type": "application/json" } }
    );
  }

  if (grantType === "refresh_token") {
    const refreshToken = params.get("refresh_token") || "";
    if (!refreshToken) {
      return oauthError(400, "invalid_request", "Missing refresh_token");
    }
    const refreshHash = await sha256Base64Url(refreshToken);
    const row = await env.DB.prepare(`
      SELECT token_hash, user_id, client_id, expires_at
      FROM oauth_refresh_tokens
      WHERE token_hash = ?
    `)
      .bind(refreshHash)
      .first<{ user_id: string; client_id: string; expires_at: string }>();
    if (!row || row.client_id !== clientId) {
      return oauthError(400, "invalid_grant", "Invalid refresh_token");
    }
    if (row.expires_at && Date.parse(row.expires_at) < Date.now()) {
      return oauthError(400, "invalid_grant", "Refresh token expired");
    }
    if (!env.JWT_SECRET) {
      return oauthError(500, "server_error", "JWT secret not configured");
    }

    const now = Math.floor(Date.now() / 1000);
    const accessToken = await signJwt(
      {
        sub: row.user_id,
        iat: now,
        exp: now + ACCESS_TOKEN_TTL_SECONDS,
        scope: "mcp",
      },
      env.JWT_SECRET
    );

    await env.DB.prepare("DELETE FROM oauth_refresh_tokens WHERE token_hash = ?")
      .bind(refreshHash)
      .run();
    const newRefreshToken = base64UrlEncode(crypto.getRandomValues(new Uint8Array(32)).buffer);
    const newRefreshHash = await sha256Base64Url(newRefreshToken);
    await env.DB.prepare(`
      INSERT INTO oauth_refresh_tokens (token_hash, user_id, client_id, expires_at, created_at)
      VALUES (?, ?, ?, datetime('now', '+${REFRESH_TOKEN_TTL_SECONDS} seconds'), datetime('now'))
    `)
      .bind(newRefreshHash, row.user_id, clientId)
      .run();

    return new Response(
      JSON.stringify({
        access_token: accessToken,
        token_type: "Bearer",
        expires_in: ACCESS_TOKEN_TTL_SECONDS,
        refresh_token: newRefreshToken,
        scope: "mcp",
      }),
      { headers: { "Content-Type": "application/json" } }
    );
  }

  return oauthError(400, "unsupported_grant_type", "Unsupported grant_type");
}

// Create the SSE route handler (legacy, for Claude Code)
const sseHandler = AceMcpAgent.mount("/sse", {
  binding: "MCP_AGENT",
  corsOptions: {
    origin: "*",
    methods: "GET, POST, OPTIONS",
    headers: "Content-Type, Authorization, mcp-session-id",
  },
});

async function handleStreamableHttp(request: Request, env: Env): Promise<Response> {
  const normalizedRequest = ensureAcceptHeader(request);
  const parsedBody = await parseJsonBody(normalizedRequest);
  const authInfo = await getAuthInfo(normalizedRequest, env);
  const requireAuth = getEnvBool(env.REQUIRE_AUTH, true);
  const effectiveAuthInfo =
    authInfo ??
    (env.DEFAULT_USER_ID
      ? { userId: env.DEFAULT_USER_ID }
      : requireAuth
        ? null
        : { userId: "anonymous" });
  if (requireAuth && !effectiveAuthInfo) {
    return jsonRpcError(401, "Unauthorized");
  }
  const authPayload = effectiveAuthInfo ?? { userId: "anonymous" };
  const server = createStreamableServer(env);
  const transport = new WebStandardStreamableHTTPServerTransport({
    sessionIdGenerator: undefined,
    enableJsonResponse: true,
  });

  await server.connect(transport);
  try {
    return await transport.handleRequest(normalizedRequest, { parsedBody, authInfo: authPayload });
  } finally {
    await transport.close();
    await server.close();
  }
}

// CORS headers for preflight
function corsHeaders(): HeadersInit {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
    "Access-Control-Allow-Headers":
      "Content-Type, Accept, Authorization, Mcp-Session-Id, mcp-session-id, mcp-protocol-version, Last-Event-ID, last-event-id",
    "Access-Control-Max-Age": "86400",
    "Access-Control-Expose-Headers": "mcp-session-id, mcp-protocol-version",
  };
}

function withCors(response: Response): Response {
  const headers = new Headers(response.headers);
  const cors = corsHeaders();
  for (const [key, value] of Object.entries(cors)) {
    if (typeof value === "string") {
      headers.set(key, value);
    }
  }
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
}

function jsonResponse(body: Record<string, unknown>, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...corsHeaders() },
  });
}

function buildIssuer(request: Request): string {
  const url = new URL(request.url);
  return url.origin;
}

function oauthMetadata(request: Request): Record<string, unknown> {
  const issuer = buildIssuer(request);
  return {
    issuer,
    authorization_endpoint: `${issuer}/oauth/authorize`,
    token_endpoint: `${issuer}/oauth/token`,
    registration_endpoint: `${issuer}/oauth/register`,
    response_types_supported: ["code"],
    grant_types_supported: ["authorization_code", "refresh_token"],
    token_endpoint_auth_methods_supported: ["client_secret_post"],
    scopes_supported: ["mcp"],
    code_challenge_methods_supported: ["S256", "plain"],
  };
}

function protectedResourceMetadata(request: Request): Record<string, unknown> {
  const issuer = buildIssuer(request);
  return {
    resource: `${issuer}/mcp`,
    authorization_servers: [issuer],
  };
}

function normalizeRedirectUris(redirectUris: string[] | null): string[] {
  if (!redirectUris) {
    return [];
  }
  return redirectUris.map((uri) => uri.trim()).filter(Boolean);
}

async function getClientRecord(
  env: Env,
  clientId: string
): Promise<{
  client_id: string;
  client_secret_hash: string;
  redirect_uris: string;
} | null> {
  return env.DB.prepare(
    "SELECT client_id, client_secret_hash, redirect_uris FROM oauth_clients WHERE client_id = ?"
  )
    .bind(clientId)
    .first<{
      client_id: string;
      client_secret_hash: string;
      redirect_uris: string;
    }>();
}

async function verifyClientCredentials(
  env: Env,
  clientId: string,
  clientSecret: string
): Promise<{ clientId: string; redirectUris: string[] } | null> {
  if (env.OAUTH_CLIENT_ID && env.OAUTH_CLIENT_SECRET) {
    if (clientId === env.OAUTH_CLIENT_ID && clientSecret === env.OAUTH_CLIENT_SECRET) {
      return { clientId, redirectUris: getAllowedRedirectUris(env) };
    }
  }

  const record = await getClientRecord(env, clientId);
  if (!record) {
    return null;
  }
  const secretHash = await sha256Base64Url(clientSecret);
  if (!timingSafeEqual(secretHash, record.client_secret_hash)) {
    return null;
  }
  let redirectUris: string[] = [];
  try {
    redirectUris = normalizeRedirectUris(JSON.parse(record.redirect_uris) as string[]);
  } catch {
    redirectUris = [];
  }
  return { clientId: record.client_id, redirectUris };
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);

    // Handle CORS preflight
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders() });
    }

    if (
      url.pathname === "/.well-known/oauth-authorization-server" ||
      url.pathname === "/.well-known/oauth-authorization-server/mcp" ||
      url.pathname === "/mcp/.well-known/oauth-authorization-server"
    ) {
      return jsonResponse(oauthMetadata(request));
    }

    if (
      url.pathname === "/.well-known/openid-configuration" ||
      url.pathname === "/.well-known/openid-configuration/mcp" ||
      url.pathname === "/mcp/.well-known/openid-configuration"
    ) {
      return jsonResponse(oauthMetadata(request));
    }

    if (
      url.pathname === "/.well-known/oauth-protected-resource" ||
      url.pathname === "/.well-known/oauth-protected-resource/mcp" ||
      url.pathname === "/mcp/.well-known/oauth-protected-resource" ||
      url.pathname === "/mcp/.well-known/oauth-protected-resource/mcp"
    ) {
      return jsonResponse(protectedResourceMetadata(request));
    }

    if (url.pathname === "/oauth/authorize") {
      if (request.method !== "GET") {
        return new Response("Method Not Allowed", { status: 405, headers: corsHeaders() });
      }
      return withCors(await handleOAuthAuthorize(request, env));
    }

    if (url.pathname === "/oauth/register") {
      return withCors(await handleOAuthRegister(request, env));
    }

    if (url.pathname === "/oauth/callback") {
      if (request.method !== "GET") {
        return new Response("Method Not Allowed", { status: 405, headers: corsHeaders() });
      }
      return withCors(await handleOAuthCallback(request, env));
    }

    if (url.pathname === "/oauth/token") {
      if (request.method !== "POST") {
        return new Response("Method Not Allowed", { status: 405, headers: corsHeaders() });
      }
      return withCors(await handleOAuthToken(request, env));
    }

    // Health check
    if (url.pathname === "/" || url.pathname === "/health") {
      return new Response(
        JSON.stringify({
          status: "ok",
          service: "ace-mcp",
          version: "2.0.0",
          transports: {
            sse: "/sse",
            streamable_http: "/mcp",
          },
          supported_clients: ["claude-code", "claude-desktop", "chatgpt", "openai-codex"],
        }),
        {
          headers: { "Content-Type": "application/json", ...corsHeaders() },
        }
      );
    }

    // SSE transport (legacy - Claude Code, Claude Desktop)
    if (url.pathname.startsWith("/sse")) {
      const requireAuth = getEnvBool(env.REQUIRE_AUTH, true);
      const authInfo = await getAuthInfo(request, env);
      if (requireAuth && !authInfo && !env.DEFAULT_USER_ID) {
        return new Response("Unauthorized", { status: 401, headers: corsHeaders() });
      }
      if (request.method === "HEAD") {
        return new Response(null, {
          status: 200,
          headers: { "Content-Type": "text/event-stream", ...corsHeaders() },
        });
      }
      return sseHandler.fetch(request, env, ctx);
    }

    // Streamable HTTP transport (new - OpenAI ChatGPT, Codex CLI)
    if (url.pathname.startsWith("/mcp")) {
      const response = await handleStreamableHttp(request, env);
      if (response.status >= 400) {
        const contentType = response.headers.get("content-type") || "";
        if (contentType.includes("application/json")) {
          try {
            const bodyText = await response.clone().text();
            console.log("MCP error response:", response.status, bodyText.slice(0, 2000));
          } catch {
            console.log("MCP error response:", response.status);
          }
        } else {
          console.log("MCP error response:", response.status);
        }
      }
      return withCors(response);
    }

    return new Response("Not Found", { status: 404, headers: corsHeaders() });
  },
};
