import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';

export function hostCompatibility(version) {
  const value = typeof version === 'string' ? version.trim().replace(/^v/, '') : '';
  const match = /^0\.2\.1-rc\.(2|3)(?:\+[^\s]+)?$/.exec(value);
  return { version: value || null, profile: match ? 'rc' + match[1] : 'unverified', verified: Boolean(match) };
}

export function detectHostCompatibility(resolve = createRequire(import.meta.url).resolve) {
  for (const name of ['@deepseek-ai/dsh/package.json', '@deepseek-ai/dsh-client-ui-settings-general/package.json']) {
    try { return hostCompatibility(JSON.parse(readFileSync(resolve(name), 'utf8')).version); }
    catch { /* An absent package does not prevent startup. */ }
  }
  return hostCompatibility(null);
}
