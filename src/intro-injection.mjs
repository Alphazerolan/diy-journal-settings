import { readFileSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { watchJournalIntro } from './journal-intro.mjs';

// Use the same selection file as skin-center, including custom skin roots.
// Missing/corrupt state never changes the application's normal startup.
export function introRows(skinDir) {
  try {
    const state = JSON.parse(readFileSync(join(dirname(dirname(skinDir)), 'skin-center-active.json'), 'utf8'));
    if (!['diy-journal', 'diy-journal-plugin'].includes(state.active) || !existsSync(join(skinDir, 'assets', 'journal-opening-v7.mp4'))) return [];
    const settingsFile = join(skinDir, 'intro-settings.json');
    if (existsSync(settingsFile) && JSON.parse(readFileSync(settingsFile, 'utf8')).introEnabled === false) return [];
    return [{ kind: 'script', placement: 'body', text:
      `;(${watchJournalIntro.toString()})(window, { early: true, delegated: ${state.active === 'diy-journal-plugin'} });` }];
  } catch { return []; }
}

export function registerIntroInjection(ctx, skinDir) {
  return ctx.on('webserver/index-inject', rows => rows.push(...introRows(skinDir)));
}
