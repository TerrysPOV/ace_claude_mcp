-- ACE (Agentic Context Engineering) D1 Database Schema
-- Supports per-user playbooks with OAuth authentication

CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    google_sub TEXT UNIQUE,
    email TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS projects (
    project_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (project_id, user_id)
);

CREATE TABLE IF NOT EXISTS entries (
    entry_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    section TEXT NOT NULL,
    content TEXT NOT NULL,
    helpful_count INTEGER DEFAULT 0,
    harmful_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (entry_id, user_id)
);

CREATE TABLE IF NOT EXISTS reflections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    task_summary TEXT NOT NULL,
    outcome TEXT NOT NULL,
    learnings TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS oauth_codes (
    code TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    redirect_uri TEXT NOT NULL,
    user_id TEXT NOT NULL,
    code_challenge TEXT NOT NULL,
    code_challenge_method TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS oauth_clients (
    client_id TEXT PRIMARY KEY,
    client_secret_hash TEXT NOT NULL,
    redirect_uris TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS oauth_refresh_tokens (
    token_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    client_id TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_entries_user_project ON entries(user_id, project_id);
CREATE INDEX IF NOT EXISTS idx_entries_user_section ON entries(user_id, project_id, section);
CREATE INDEX IF NOT EXISTS idx_reflections_user ON reflections(user_id, project_id);
CREATE INDEX IF NOT EXISTS idx_oauth_codes_user ON oauth_codes(user_id);
CREATE INDEX IF NOT EXISTS idx_oauth_refresh_user ON oauth_refresh_tokens(user_id);
