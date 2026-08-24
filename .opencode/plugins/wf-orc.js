import { readFileSync, readdirSync } from 'fs';
import { join } from 'path';
import { fileURLToPath } from 'url';

const __dirname = import.meta.dirname || join(fileURLToPath(import.meta.url), '..');
const ROOT = join(__dirname, '..', '..');

// Tool name → OpenCode permission key
const TOOL_MAP = {
  read_file: 'read',
  grep_search: 'grep',
  glob: 'glob',
  list_directory: 'glob',
  write_file: 'edit',
  edit: 'edit',
  run_shell_command: 'bash',
  web_fetch: 'webfetch',
};

function parseFrontmatter(content) {
  const match = content.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
  if (!match) return { meta: {}, body: content };

  const meta = {};
  for (const line of match[1].split('\n')) {
    const colonIdx = line.indexOf(':');
    if (colonIdx === -1) continue;
    const key = line.slice(0, colonIdx).trim();
    const val = line.slice(colonIdx + 1).trim();
    if (!key) continue;

    if (val.startsWith('[') && val.endsWith(']')) {
      meta[key] = val.slice(1, -1).split(',').map(s => s.trim()).filter(Boolean);
    } else if (val.startsWith('"') && val.endsWith('"')) {
      meta[key] = val.slice(1, -1);
    } else if (val === 'true') {
      meta[key] = true;
    } else if (val === 'false') {
      meta[key] = false;
    } else if (/^\d+$/.test(val)) {
      meta[key] = parseInt(val, 10);
    } else {
      meta[key] = val;
    }
  }
  return { meta, body: match[2] };
}

function convertAgent(meta) {
  const agent = {
    description: meta.description || '',
    mode: 'subagent',
  };

  if (meta.maxTurns) agent.steps = meta.maxTurns;

  // Convert tools whitelist → permission allow
  if (Array.isArray(meta.tools) && meta.tools.length > 0) {
    const perm = {};
    for (const tool of meta.tools) {
      const key = TOOL_MAP[tool];
      if (key) perm[key] = 'allow';
    }
    agent.permission = perm;
  }

  // Convert disallowedTools blacklist → permission deny
  if (Array.isArray(meta.disallowedTools) && meta.disallowedTools.length > 0) {
    const perm = agent.permission || {};
    for (const tool of meta.disallowedTools) {
      const key = TOOL_MAP[tool];
      if (key) perm[key] = 'deny';
    }
    agent.permission = perm;
  }

  return agent;
}

function loadAgents() {
  const agentsDir = join(ROOT, 'agents');
  const agents = {};
  try {
    for (const file of readdirSync(agentsDir).filter(f => f.endsWith('.md'))) {
      const name = file.replace('.md', '');
      const content = readFileSync(join(agentsDir, file), 'utf-8');
      const { meta } = parseFrontmatter(content);
      agents[`wf-orc-${name}`] = convertAgent(meta);
    }
  } catch (e) {
    // agents dir not found
  }
  return agents;
}

function loadCommands() {
  const commandsDir = join(ROOT, 'commands', 'wf-orc');
  const commands = {};
  try {
    for (const file of readdirSync(commandsDir).filter(f => f.endsWith('.md'))) {
      const name = `wf-orc-${file.replace('.md', '')}`;
      const content = readFileSync(join(commandsDir, file), 'utf-8');
      const { meta, body } = parseFrontmatter(content);
      commands[name] = {
        description: meta.description || `Run wf-orc ${name} workflow`,
        template: body.replace(/\{\{args\}\}/g, '$ARGUMENTS').trim(),
      };
    }
  } catch (e) {
    // commands dir not found
  }
  return commands;
}

export const WfOrcPlugin = async ({ directory }) => {
  return {
    config: async (config) => {
      // Register skills path
      config.skills = config.skills || {};
      config.skills.paths = config.skills.paths || [];
      const skillsPath = join(ROOT, 'skills');
      if (!config.skills.paths.includes(skillsPath)) {
        config.skills.paths.push(skillsPath);
      }

      // Register agents
      const agents = loadAgents();
      config.agent = { ...agents, ...(config.agent || {}) };

      // Register commands
      const commands = loadCommands();
      config.command = { ...commands, ...(config.command || {}) };

      return config;
    },
  };
};

export default WfOrcPlugin;
