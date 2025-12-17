-- ACE (Agentic Context Engineering) D1 Database Schema
-- Supports multi-project playbooks with global entries

CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS entries (
    id TEXT PRIMARY KEY,
    project_id TEXT DEFAULT 'global',
    section TEXT NOT NULL,
    content TEXT NOT NULL,
    helpful INTEGER DEFAULT 0,
    harmful INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reflections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT DEFAULT 'global',
    task_summary TEXT NOT NULL,
    outcome TEXT NOT NULL,
    learnings TEXT NOT NULL,  -- JSON array
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert global project
INSERT OR IGNORE INTO projects (id, description) VALUES ('global', 'Universal patterns and insights shared across all projects');

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_entries_project ON entries(project_id);
CREATE INDEX IF NOT EXISTS idx_entries_section ON entries(project_id, section);
CREATE INDEX IF NOT EXISTS idx_reflections_project ON reflections(project_id);

-- Default global entries
INSERT OR IGNORE INTO entries (id, project_id, section, content, helpful, harmful) VALUES
    ('str-00001', 'global', 'STRATEGIES & INSIGHTS', 'Break complex problems into smaller, manageable steps.', 0, 0),
    ('str-00002', 'global', 'STRATEGIES & INSIGHTS', 'Validate assumptions before proceeding with solutions.', 0, 0),
    ('cal-00001', 'global', 'FORMULAS & CALCULATIONS', 'ROI = (Gain - Cost) / Cost * 100', 0, 0),
    ('mis-00001', 'global', 'COMMON MISTAKES TO AVOID', 'Don''t assume input data is clean - always validate.', 0, 0),
    ('dom-00001', 'global', 'DOMAIN KNOWLEDGE', 'Context window limits require prioritizing relevant information.', 0, 0);
