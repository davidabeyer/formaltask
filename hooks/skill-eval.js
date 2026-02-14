#!/usr/bin/env node
/**
 * Skill Evaluation v4.1 - antirez style
 *
 * Simple: does the user's prompt overlap with the skill description?
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

const SKILL_DIRS = [
  path.join(os.homedir(), 'claude-code', 'skills'),
  path.join(os.homedir(), '.claude', 'skills'),
];

const STOPWORDS = new Set(['this', 'that', 'with', 'from', 'when', 'should', 'used', 'user', 'code', 'file', 'help']);

function loadAllSkills() {
  const seen = new Set();
  const skills = [];

  for (const dir of SKILL_DIRS) {
    if (!fs.existsSync(dir)) continue;

    const entries = fs.readdirSync(dir, { withFileTypes: true });

    for (const e of entries) {
      if (!e.isDirectory()) continue;
      if (seen.has(e.name)) continue; // Skip duplicates
      seen.add(e.name);

      const file = path.join(dir, e.name, 'SKILL.md');
      if (!fs.existsSync(file)) continue;

      const content = fs.readFileSync(file, 'utf-8');
      const name = e.name;

      // Get description from frontmatter
      const match = content.match(/description:\s*>?-?\s*\n?([\s\S]*?)(?=\n---|\n\w+:)/i);
      const desc = match ? match[1].replace(/[^\w\s]/g, ' ').toLowerCase() : '';

      if (desc.length > 20) {
        const priority = /must be used|critical|always/.test(desc) ? 9 : 5;
        skills.push({ name, desc, priority });
      }
    }
  }

  return skills;
}

function score(promptWords, skill) {
  let s = 0;
  const reasons = [];

  // Name match
  const nameWords = skill.name.split('-');
  for (const w of nameWords) {
    if (promptWords.includes(w)) {
      s += 5;
      reasons.push(w);
    }
  }

  // Prompt words found in description
  for (const w of promptWords) {
    if (w.length < 4 || STOPWORDS.has(w)) continue;
    if (skill.desc.includes(w)) {
      s += 2;
      if (reasons.length < 4) reasons.push(w);
    }
  }

  return { s, reasons: [...new Set(reasons)] };
}

// Main
let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', c => input += c);
process.stdin.on('end', () => {
  let prompt;
  try { prompt = JSON.parse(input).prompt || ''; }
  catch { prompt = input; }

  if (!prompt.trim()) process.exit(0);

  // Extract words from prompt
  const promptWords = prompt.toLowerCase().replace(/[^\w\s]/g, ' ').split(/\s+/).filter(w => w.length > 2);

  const skills = loadAllSkills();
  const matches = skills
    .map(sk => ({ name: sk.name, priority: sk.priority, ...score(promptWords, sk) }))
    .filter(m => m.s >= 4)
    .sort((a, b) => b.s - a.s || b.priority - a.priority)
    .slice(0, 5);

  if (!matches.length) process.exit(0);

  let out = '<user-prompt-submit-hook>\nSKILL SUGGESTIONS\n\n';
  for (const m of matches) {
    out += `- ${m.name} (${m.reasons.join(', ')})\n`;
  }
  out += '</user-prompt-submit-hook>';

  console.log(out);
});
