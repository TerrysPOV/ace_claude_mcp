/**
 * ACE (Agentic Context Engineering) MCP Server for Cloudflare Workers
 *
 * Provides MCP tools for managing evolving playbooks with D1 database backend.
 * Supports multi-project playbooks with global + project-specific entries.
 */

import { McpAgent } from "agents/mcp";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";

interface Env {
  DB: D1Database;
}

// Section prefixes for ID generation
const SECTION_PREFIXES: Record<string, string> = {
  "STRATEGIES & INSIGHTS": "str",
  "FORMULAS & CALCULATIONS": "cal",
  "COMMON MISTAKES TO AVOID": "mis",
  "DOMAIN KNOWLEDGE": "dom",
};

const VALID_SECTIONS = Object.keys(SECTION_PREFIXES);

// Helper: Generate next ID for a section
async function getNextId(db: D1Database, prefix: string): Promise<string> {
  const result = await db.prepare(
    `SELECT id FROM entries WHERE id LIKE ? ORDER BY id DESC LIMIT 1`
  ).bind(`${prefix}-%`).first<{ id: string }>();

  if (result) {
    const num = parseInt(result.id.split("-")[1], 10);
    return `${prefix}-${String(num + 1).padStart(5, "0")}`;
  }
  return `${prefix}-00001`;
}

// Helper: Format entries as markdown playbook
function formatPlaybook(entries: Array<{ id: string; section: string; content: string; helpful: number; harmful: number; project_id: string }>): string {
  const sections: Record<string, string[]> = {};

  for (const entry of entries) {
    if (!sections[entry.section]) {
      sections[entry.section] = [];
    }
    const marker = entry.project_id === "global" ? "" : ` [${entry.project_id}]`;
    sections[entry.section].push(
      `[${entry.id}] helpful=${entry.helpful} harmful=${entry.harmful}${marker} :: ${entry.content}`
    );
  }

  const lines: string[] = [];
  for (const section of VALID_SECTIONS) {
    if (sections[section] && sections[section].length > 0) {
      lines.push(`## ${section}`);
      lines.push(...sections[section]);
      lines.push("");
    }
  }

  return lines.join("\n");
}

// Helper: Calculate similarity between two strings
function similarity(a: string, b: string): number {
  const aLower = a.toLowerCase();
  const bLower = b.toLowerCase();

  if (aLower === bLower) return 1;
  if (aLower.length < 2 || bLower.length < 2) return 0;

  const bigrams = new Map<string, number>();
  for (let i = 0; i < aLower.length - 1; i++) {
    const bigram = aLower.substring(i, i + 2);
    bigrams.set(bigram, (bigrams.get(bigram) || 0) + 1);
  }

  let intersectionSize = 0;
  for (let i = 0; i < bLower.length - 1; i++) {
    const bigram = bLower.substring(i, i + 2);
    const count = bigrams.get(bigram) || 0;
    if (count > 0) {
      bigrams.set(bigram, count - 1);
      intersectionSize++;
    }
  }

  return (2.0 * intersectionSize) / (aLower.length + bLower.length - 2);
}

export class AceMcpAgent extends McpAgent<Env> {
  server = new McpServer({
    name: "ace",
    version: "2.0.0",
  });

  async init() {
    // Tool: read_playbook
    this.server.tool(
      "read_playbook",
      "Return the full playbook content, merging global entries with project-specific entries",
      {
        project_id: z.string().optional().describe("Project ID to read (default: 'global'). Merges global + project entries."),
      },
      async ({ project_id = "global" }) => {
        const entries = await this.env.DB.prepare(`
          SELECT id, project_id, section, content, helpful, harmful
          FROM entries
          WHERE project_id = 'global' OR project_id = ?
          ORDER BY section, project_id = 'global' DESC, id
        `).bind(project_id).all<{ id: string; project_id: string; section: string; content: string; helpful: number; harmful: number }>();

        return { content: [{ type: "text", text: formatPlaybook(entries.results || []) }] };
      }
    );

    // Tool: get_section
    this.server.tool(
      "get_section",
      "Get all entries from a specific section of the playbook",
      {
        section: z.enum(VALID_SECTIONS as [string, ...string[]]).describe("Section name"),
        project_id: z.string().optional().describe("Project ID (default: includes global + this project)"),
      },
      async ({ section, project_id = "global" }) => {
        const entries = await this.env.DB.prepare(`
          SELECT id, project_id, section, content, helpful, harmful
          FROM entries
          WHERE section = ? AND (project_id = 'global' OR project_id = ?)
          ORDER BY project_id = 'global' DESC, id
        `).bind(section, project_id).all<{ id: string; project_id: string; section: string; content: string; helpful: number; harmful: number }>();

        const formatted = formatPlaybook(entries.results || []);
        return { content: [{ type: "text", text: formatted || `No entries in section '${section}'` }] };
      }
    );

    // Tool: add_entry
    this.server.tool(
      "add_entry",
      "Add a new entry to the playbook with auto-generated ID",
      {
        section: z.enum(VALID_SECTIONS as [string, ...string[]]).describe("Section to add entry to"),
        content: z.string().describe("The insight, formula, or knowledge to add"),
        project_id: z.string().optional().describe("Project ID (default: 'global' for universal patterns)"),
      },
      async ({ section, content, project_id = "global" }) => {
        const prefix = SECTION_PREFIXES[section];
        const newId = await getNextId(this.env.DB, prefix);

        await this.env.DB.prepare(`
          INSERT INTO entries (id, project_id, section, content, helpful, harmful)
          VALUES (?, ?, ?, ?, 0, 0)
        `).bind(newId, project_id, section, content.trim()).run();

        return { content: [{ type: "text", text: `Added entry [${newId}] to '${section}' (project: ${project_id})` }] };
      }
    );

    // Tool: update_counters
    this.server.tool(
      "update_counters",
      "Update the helpful/harmful counters for an entry",
      {
        entry_id: z.string().describe("Entry ID (e.g., 'str-00001')"),
        helpful_delta: z.number().describe("Amount to add to helpful counter"),
        harmful_delta: z.number().describe("Amount to add to harmful counter"),
      },
      async ({ entry_id, helpful_delta, harmful_delta }) => {
        const entry = await this.env.DB.prepare(
          `SELECT helpful, harmful FROM entries WHERE id = ?`
        ).bind(entry_id).first<{ helpful: number; harmful: number }>();

        if (!entry) {
          return { content: [{ type: "text", text: `Entry '${entry_id}' not found.` }] };
        }

        const newHelpful = Math.max(0, entry.helpful + helpful_delta);
        const newHarmful = Math.max(0, entry.harmful + harmful_delta);

        await this.env.DB.prepare(`
          UPDATE entries SET helpful = ?, harmful = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?
        `).bind(newHelpful, newHarmful, entry_id).run();

        return { content: [{ type: "text", text: `Updated [${entry_id}]: helpful=${entry.helpful}->${newHelpful}, harmful=${entry.harmful}->${newHarmful}` }] };
      }
    );

    // Tool: remove_entry
    this.server.tool(
      "remove_entry",
      "Remove an entry from the playbook by its ID",
      {
        entry_id: z.string().describe("Entry ID to remove"),
      },
      async ({ entry_id }) => {
        const result = await this.env.DB.prepare(
          `DELETE FROM entries WHERE id = ?`
        ).bind(entry_id).run();

        if (result.meta.changes === 0) {
          return { content: [{ type: "text", text: `Entry '${entry_id}' not found.` }] };
        }
        return { content: [{ type: "text", text: `Removed entry [${entry_id}]` }] };
      }
    );

    // Tool: log_reflection
    this.server.tool(
      "log_reflection",
      "Log a task reflection for later curation into the playbook",
      {
        task_summary: z.string().describe("Brief description of the task"),
        outcome: z.enum(["success", "partial", "failure"]).describe("Task outcome"),
        learnings: z.array(z.string()).describe("List of insights or lessons learned"),
        project_id: z.string().optional().describe("Project ID (default: 'global')"),
      },
      async ({ task_summary, outcome, learnings, project_id = "global" }) => {
        await this.env.DB.prepare(`
          INSERT INTO reflections (project_id, task_summary, outcome, learnings)
          VALUES (?, ?, ?, ?)
        `).bind(project_id, task_summary, outcome, JSON.stringify(learnings)).run();

        return { content: [{ type: "text", text: `Logged reflection with ${learnings.length} learning(s) for: ${task_summary.slice(0, 50)}...` }] };
      }
    );

    // Tool: curate_playbook
    this.server.tool(
      "curate_playbook",
      "Curate the playbook by removing harmful entries and finding duplicates",
      {
        project_id: z.string().optional().describe("Project to curate (default: all projects)"),
        harmful_threshold: z.number().optional().describe("Remove entries where harmful > helpful + threshold (default: 3)"),
      },
      async ({ project_id, harmful_threshold = 3 }) => {
        // Remove harmful entries
        let deleteQuery = `DELETE FROM entries WHERE harmful > helpful + ?`;
        const params: (string | number)[] = [harmful_threshold];

        if (project_id) {
          deleteQuery += ` AND project_id = ?`;
          params.push(project_id);
        }

        const deleteResult = await this.env.DB.prepare(deleteQuery).bind(...params).run();
        const removed = deleteResult.meta.changes || 0;

        // Find duplicates
        let selectQuery = `SELECT id, content FROM entries`;
        if (project_id) {
          selectQuery += ` WHERE project_id = ? OR project_id = 'global'`;
        }

        const entries = project_id
          ? await this.env.DB.prepare(selectQuery).bind(project_id).all<{ id: string; content: string }>()
          : await this.env.DB.prepare(selectQuery).all<{ id: string; content: string }>();

        const duplicates: string[] = [];
        const results = entries.results || [];
        for (let i = 0; i < results.length; i++) {
          for (let j = i + 1; j < results.length; j++) {
            const sim = similarity(results[i].content, results[j].content);
            if (sim > 0.8) {
              duplicates.push(`${results[i].id} ~ ${results[j].id} (${Math.round(sim * 100)}%)`);
            }
          }
        }

        const lines = [];
        lines.push(removed > 0 ? `Removed ${removed} harmful entries.` : "No harmful entries to remove.");
        if (duplicates.length > 0) {
          lines.push(`Potential duplicates: ${duplicates.slice(0, 5).join("; ")}`);
          if (duplicates.length > 5) lines.push(`  ...and ${duplicates.length - 5} more`);
        } else {
          lines.push("No duplicate entries found.");
        }

        return { content: [{ type: "text", text: lines.join("\n") }] };
      }
    );

    // Tool: search_playbook
    this.server.tool(
      "search_playbook",
      "Search the playbook for entries containing keywords",
      {
        query: z.string().describe("Keywords to search for (space-separated)"),
        project_id: z.string().optional().describe("Project ID to search within (includes global)"),
      },
      async ({ query, project_id = "global" }) => {
        const keywords = query.toLowerCase().split(/\s+/);

        const entries = await this.env.DB.prepare(`
          SELECT id, project_id, section, content, helpful, harmful
          FROM entries
          WHERE project_id = 'global' OR project_id = ?
        `).bind(project_id).all<{ id: string; project_id: string; section: string; content: string; helpful: number; harmful: number }>();

        const matches = (entries.results || []).filter(e =>
          keywords.some(kw => e.content.toLowerCase().includes(kw))
        );

        if (matches.length === 0) {
          return { content: [{ type: "text", text: `No entries found matching '${query}'` }] };
        }

        const formatted = matches.map(e => {
          const marker = e.project_id === "global" ? "" : ` [${e.project_id}]`;
          return `[${e.id}] helpful=${e.helpful} harmful=${e.harmful}${marker} :: ${e.content}`;
        }).join("\n");

        return { content: [{ type: "text", text: `Found ${matches.length} matching entries:\n${formatted}` }] };
      }
    );

    // Tool: list_projects
    this.server.tool(
      "list_projects",
      "List all projects in the playbook system",
      {},
      async () => {
        const projects = await this.env.DB.prepare(`
          SELECT id, description, created_at FROM projects ORDER BY created_at
        `).all<{ id: string; description: string | null; created_at: string }>();

        const lines = (projects.results || []).map(p =>
          `- ${p.id}${p.description ? `: ${p.description}` : ""}`
        );

        return { content: [{ type: "text", text: lines.length > 0 ? lines.join("\n") : "No projects found." }] };
      }
    );

    // Tool: create_project
    this.server.tool(
      "create_project",
      "Create a new project for organizing domain-specific playbook entries",
      {
        project_id: z.string().describe("Unique project identifier (e.g., 'finance', 'web-dev')"),
        description: z.string().optional().describe("Brief description of the project domain"),
      },
      async ({ project_id, description }) => {
        try {
          await this.env.DB.prepare(`
            INSERT INTO projects (id, description) VALUES (?, ?)
          `).bind(project_id, description || null).run();

          return { content: [{ type: "text", text: `Created project '${project_id}'${description ? `: ${description}` : ""}` }] };
        } catch (e: any) {
          if (e.message?.includes("UNIQUE constraint")) {
            return { content: [{ type: "text", text: `Project '${project_id}' already exists.` }] };
          }
          throw e;
        }
      }
    );
  }
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);

    // Health check
    if (url.pathname === "/" || url.pathname === "/health") {
      return new Response(JSON.stringify({
        status: "ok",
        service: "ace-mcp",
        version: "2.0.0"
      }), {
        headers: { "Content-Type": "application/json" }
      });
    }

    // MCP SSE endpoint
    if (url.pathname === "/sse" || url.pathname === "/sse/message") {
      const agent = new AceMcpAgent(env, ctx);
      await agent.init();
      return agent.fetch(request);
    }

    return new Response("Not Found", { status: 404 });
  },
};
