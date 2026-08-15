/* U14 live rehearsal driver for the Android emulator: drives the installed app
 * through the parent sign-in and captures the four approved states via adb
 * screencap, asserting the UI tree (uiautomator) per state.
 */
const {execFileSync} = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

const ADB =
  process.env.ADB_PATH ||
  'C:\\Users\\zyonn\\AppData\\Local\\Android\\Sdk\\platform-tools\\adb.exe';
const DEVICE = process.env.ANDROID_DEVICE || 'emulator-5554';
const WORKTREE = path.resolve(__dirname, '..');
const SEED_SCRIPT = path.join(__dirname, 'seed_parent_dashboard_live.js');
const OUT_DIR = path.join(
  WORKTREE,
  'docs',
  'evidence',
  '2026-08-15-u14-screenshots',
);

const EMAIL = 'parent-live@example.test';
const PASSWORD = 'parent-dashboard-test-password';

function adb(...args) {
  return execFileSync(ADB, ['-s', DEVICE, ...args], {encoding: 'utf8'});
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function uiDump() {
  adb('shell', 'uiautomator', 'dump', '/sdcard/u14-ui.xml');
  const xml = adb('shell', 'cat', '/sdcard/u14-ui.xml');
  const nodes = [];
  const re =
    /<node[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"[^>]*>/g;
  let match;
  while ((match = re.exec(xml))) {
    const [full, x1, y1, x2, y2] = match;
    const text = /text="([^"]*)"/.exec(full);
    const desc = /content-desc="([^"]*)"/.exec(full);
    const cls = /class="([^"]*)"/.exec(full);
    const label = (text && text[1]) || (desc && desc[1]) || '';
    nodes.push({
      label,
      cls: cls ? cls[1] : '',
      x: Math.round((+x1 + +x2) / 2),
      y: Math.round((+y1 + +y2) / 2),
      w: +x2 - +x1,
      h: +y2 - +y1,
    });
  }
  return nodes;
}

async function waitForUi(fragment, {timeout = 60000} = {}) {
  const start = Date.now();
  for (;;) {
    const nodes = uiDump();
    const hit = nodes.find(
      (n) => n.label.includes(fragment) && n.w > 0 && n.h > 0,
    );
    if (hit) return hit;
    if (Date.now() - start > timeout) {
      throw new Error(`Timed out waiting for UI: ${fragment}`);
    }
    await sleep(1500);
  }
}

async function tapLabel(fragment) {
  const node = await waitForUi(fragment);
  adb('shell', 'input', 'tap', `${node.x} ${node.y}`);
  await sleep(1500);
}

async function uiText() {
  return uiDump()
    .map((n) => n.label)
    .filter(Boolean)
    .join('\n');
}

async function typeInto(fragment, text) {
  await tapLabel(fragment);
  await sleep(600);
  const safe = text
    .replace(/ /g, '%s')
    .replace(/&/g, '\\&')
    .replace(/\(/g, '\\(')
    .replace(/\)/g, '\\)');
  adb('shell', 'input', 'text', safe);
  await sleep(600);
}

async function screenshot(name) {
  const file = path.join(OUT_DIR, name);
  const buffer = execFileSync(ADB, ['-s', DEVICE, 'exec-out', 'screencap', '-p']);
  fs.writeFileSync(file, buffer);
  return {file, bytes: buffer.length};
}

async function signIn() {
  await waitForUi('Parent Dashboard');
  await tapLabel('Parent Dashboard');
  await waitForUi('Private parent access');
  await sleep(1500);
  await typeInto('Parent email', EMAIL);
  await typeInto('Password', PASSWORD);
  await tapLabel('Secure parent sign in');
  await waitForUi('Safe learning updates for Aiman', {timeout: 60000});
  await sleep(2500);
}

async function captureState(name) {
  const spec = STATES[name];
  execFileSync('node', [SEED_SCRIPT, '--state', spec.seed], {
    cwd: WORKTREE,
    stdio: 'pipe',
  });
  // Reload the app so the parent session restarts against the new fixtures.
  adb('shell', 'am', 'force-stop', 'com.example.logic_oasis');
  await sleep(1000);
  adb('shell', 'monkey', '-p', 'com.example.logic_oasis', '-c',
    'android.intent.category.LAUNCHER', '1');
  await sleep(8000);
  await signIn();
  const text = await uiText();
  const missing = spec.include.filter((entry) => !text.includes(entry));
  const unwanted = spec.exclude.filter((entry) => text.includes(entry));
  const shot = await screenshot(`live-${name}.png`);
  return {name, missing, unwanted, ...shot};
}

const STATES = {
  full: {
    seed: 'full',
    include: [
      'Safe learning updates for Aiman',
      'Learning snapshot',
      'A steady week with a clear focus',
      'Mon: 1',
      'Fri: 1',
      '1 question asked',
      '2 replies',
    ],
    exclude: ['No practice completed yet this week'],
  },
  partial: {
    seed: 'partial',
    include: ['Safe learning updates for Aiman', 'Learning snapshot', 'Mon: 1'],
    exclude: ['No practice completed yet this week'],
  },
  zero: {
    seed: 'zero',
    include: [
      'Safe learning updates for Aiman',
      'No practice completed yet this week',
      'No Mutual Aid moments yet this week',
      'More recent learning evidence is needed',
    ],
    exclude: ['Mon: 1'],
  },
  insufficient: {
    seed: 'insufficient',
    include: [
      'Safe learning updates for Aiman',
      'More recent learning evidence is needed',
    ],
    exclude: ['Mon: 1'],
  },
};

(async () => {
  fs.mkdirSync(OUT_DIR, {recursive: true});
  await signIn();
  const results = [];
  for (const name of ['full', 'partial', 'zero', 'insufficient']) {
    results.push(await captureState(name));
  }
  const failed = results.filter((r) => r.missing.length || r.unwanted.length);
  console.log(
    JSON.stringify(
      {
        status: failed.length ? 'assertions-failed' : 'passed',
        device: DEVICE,
        results,
      },
      null,
      2,
    ),
  );
  if (failed.length) process.exitCode = 1;
})().catch((error) => {
  console.error(JSON.stringify({status: 'failed', message: error.message}, null, 2));
  process.exitCode = 1;
});
