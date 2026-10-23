import { readFileSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { watchJournalIntro } from './journal-intro.mjs';

// Use the same selection file as skin-center, including custom skin roots.
// Missing/corrupt state never changes the application's normal startup.
export function introRows(skinDir) {
  try {
    const state = JSON.parse(readFileSync(join(dirname(dirname(skinDir)), 'skin-center-active.json'), 'utf8'));
    if (state.active !== 'diy-journal' || !existsSync(join(skinDir, 'assets', 'journal-opening-v7.mp4'))) return [];
    return [{ kind: 'script', placement: 'body', text:
      `;(${watchJournalIntro.toString()})(window, { early: true });` }];
  } catch { return []; }
}

export function registerIntroInjection(ctx, skinDir) {
  return ctx.on('webserver/index-inject', rows => rows.push(...introRows(skinDir)));
}
