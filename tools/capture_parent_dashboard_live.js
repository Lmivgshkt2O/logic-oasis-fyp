/* U14 live rehearsal driver: drives the running Flutter web app in headless
 * Chrome over the DevTools Protocol, signs in as the seeded linked parent,
 * captures the four approved states as text-accurate PNG screenshots, and
 * asserts the expected copy per state.
 *
 * Prerequisites (run in order):
 *   1. Firebase emulators (auth 9099, firestore 8080, functions 5001)
 *   2. node tools/seed_parent_dashboard_live.js --state full
 *   3. flutter run -d web-server --web-port 8123 --dart-define=USE_FIREBASE_EMULATORS=true
 *
 * Usage:
 *   node tools/capture_parent_dashboard_live.js --probe
 *   node tools/capture_parent_dashboard_live.js
 */
const {execFileSync, spawn} = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const CHROME =
  process.env.CHROME_PATH ||
  'C:\\Users\\zyonn\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe';
const APP_URL = process.env.APP_URL || 'http://127.0.0.1:8123';
// Unique per run: an orphaned Chrome child can hold the debug port after a
// crash, so never reuse a fixed port.
const CDP_PORT = 9200 + (process.pid % 400);
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
const FIREFOX_UA =
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:136.0) Gecko/20100101 Firefox/136.0';

const STATES = {
  full: {
    seed: 'full',
    include: [
      'Safe learning updates for Aiman',
      'Learning snapshot',
      'A steady week with a clear focus',
      'Focus: Recognise and Write Numbers',
      'Based on 2 trusted learning observations',
      'Mon: 1',
      'Fri: 1',
      '1 question asked',
      '2 replies',
      '1 accepted',
    ],
    exclude: ['No practice completed yet this week', 'temporarily unavailable'],
  },
  partial: {
    seed: 'partial',
    include: [
      'Safe learning updates for Aiman',
      'Learning snapshot',
      'A steady week with a clear focus',
      'Mon: 1',
      '2 replies',
    ],
    exclude: [
      'Compared with',
      'No practice completed yet this week',
      'temporarily unavailable',
    ],
  },
  zero: {
    seed: 'zero',
    include: [
      'Safe learning updates for Aiman',
      'No practice completed yet this week',
      'No Mutual Aid moments yet this week',
      'More recent learning evidence is needed',
    ],
    exclude: ['Compared with', 'Mon: 1'],
  },
  insufficient: {
    seed: 'insufficient',
    include: [
      'Safe learning updates for Aiman',
      'More recent learning evidence is needed',
      'Practice effort is unavailable this week',
      'Participation summary is unavailable this week',
    ],
    exclude: ['Mon: 1', '2 replies'],
  },
};

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

class Cdp {
  constructor(ws) {
    this.ws = ws;
    this.id = 0;
    this.pending = new Map();
    this.events = [];
  }

  static async connect(url) {
    const ws = new WebSocket(url);
    await new Promise((resolve, reject) => {
      ws.onopen = resolve;
      ws.onerror = () => reject(new Error('CDP websocket failed to open'));
    });
    const cdp = new Cdp(ws);
    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.method) {
        cdp.events.push(message);
      }
      if (!message.id || !cdp.pending.has(message.id)) return;
      const {resolve, reject} = cdp.pending.get(message.id);
      cdp.pending.delete(message.id);
      if (message.error) {
        reject(new Error(`${message.error.code}: ${message.error.message}`));
      } else {
        resolve(message.result);
      }
    };
    return cdp;
  }

  send(method, params = {}) {
    const id = ++this.id;
    return new Promise((resolve, reject) => {
      this.pending.set(id, {resolve, reject});
      this.ws.send(JSON.stringify({id, method, params}));
    });
  }

  async evaluate(expression) {
    const result = await this.send('Runtime.evaluate', {
      expression,
      returnByValue: true,
      awaitPromise: true,
    });
    if (result.exceptionDetails) {
      throw new Error(
        `Evaluation failed for: ${expression}\n  -> ${JSON.stringify(result.exceptionDetails.exception || result.exceptionDetails.text)}`,
      );
    }
    return result.result.value;
  }
}

async function waitFor(fn, {timeout = 120000, interval = 500, label}) {
  const start = Date.now();
  for (;;) {
    try {
      const value = await fn();
      if (value) return value;
    } catch (_) {
      // keep polling
    }
    if (Date.now() - start > timeout) {
      throw new Error(`Timed out waiting for: ${label}`);
    }
    await sleep(interval);
  }
}

async function semantics() {
  return cdp.evaluate(`(() => {
    const nodes = [...document.querySelectorAll('flt-semantics')];
    return nodes.map((n) => {
      const r = n.getBoundingClientRect();
      return {
        role: n.getAttribute('role'),
        label: (n.getAttribute('aria-label') || '').trim(),
        text: (n.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 160),
        x: Math.round(r.x),
        y: Math.round(r.y),
        w: Math.round(r.width),
        h: Math.round(r.height),
      };
    }).filter((n) => n.label || n.text || n.role);
  })()`);
}

async function pageText() {
  return cdp.evaluate(`(() => {
    const parts = [];
    document.querySelectorAll('flt-semantics').forEach((n) => {
      const label = (n.getAttribute('aria-label') || '').trim();
      if (label) parts.push(label);
    });
    if (document.body && document.body.innerText) parts.push(document.body.innerText);
    return parts.join('\\n');
  })()`);
}

async function findNode(fragment, exact = false) {
  const nodes = await semantics();
  const matches = nodes.filter((n) =>
    exact
      ? n.label === fragment
      : n.label.includes(fragment) || n.text.includes(fragment),
  );
  const interactive =
    matches.find((n) => n.role === 'button' || n.role === 'textbox') ||
    matches.find((n) => n.role === 'checkbox');
  return interactive || matches[0];
}

async function enableSemantics() {
  await waitFor(
    () =>
      cdp.evaluate(
        `!!document.querySelector('flutter-view') && !!document.querySelector('flt-semantics-placeholder')`,
      ),
    {label: 'flutter view + placeholder', timeout: 60000},
  );
  await cdp.evaluate(`(() => {
    const placeholder = document.querySelector('flt-semantics-placeholder');
    if (placeholder) {
      placeholder.dispatchEvent(
        new MouseEvent('click', {bubbles: true, cancelable: true}),
      );
    }
    return !!placeholder;
  })()`);
  await waitFor(
    () =>
      cdp.evaluate(
        `document.querySelectorAll('flt-semantics').length > 0`,
      ),
    {label: 'semantics tree', timeout: 60000},
  );
}

async function clickFragment(fragment, exact = false) {
  const node = await waitFor(
    () => findNode(fragment, exact),
    {label: `node ${fragment}`},
  );
  await cdp.evaluate(`(() => {
    const nodes = [...document.querySelectorAll('flt-semantics')];
    const n = nodes.find((el) => {
      const label = (el.getAttribute('aria-label') || '').trim();
      const text = (el.textContent || '').trim();
      return ${exact ? 'label === ' : 'label.includes('}${JSON.stringify(fragment)}${exact ? '' : ')'}${exact ? '' : ' || text.includes(' + JSON.stringify(fragment) + ')'};
    });
    if (n) n.click();
    return !!n;
  })()`);
  const x = node.x + node.w / 2;
  const y = node.y + node.h / 2;
  await cdp.send('Input.dispatchMouseEvent', {
    type: 'mousePressed',
    x,
    y,
    button: 'left',
    clickCount: 1,
  });
  await cdp.send('Input.dispatchMouseEvent', {
    type: 'mouseReleased',
    x,
    y,
    button: 'left',
    clickCount: 1,
  });
  await sleep(300);
}

async function mouseClick(x, y) {
  await cdp.send('Input.dispatchMouseEvent', {
    type: 'mousePressed',
    x,
    y,
    button: 'left',
    clickCount: 1,
  });
  await cdp.send('Input.dispatchMouseEvent', {
    type: 'mouseReleased',
    x,
    y,
    button: 'left',
    clickCount: 1,
  });
  await sleep(300);
}

async function typeAt(x, y, text) {
  await mouseClick(x, y);
  await cdp.send('Input.insertText', {text});
  await sleep(250);
}

async function focusAndType(candidates, text, label) {
  for (const [x, y] of candidates) {
    await mouseClick(x, y);
    const value = await focusedInputValue();
    if (value !== null) {
      await cdp.send('Input.insertText', {text});
      await sleep(250);
      const after = await focusedInputValue();
      if (after === text) return true;
    }
  }
  await dumpSemantics(`could not type ${label}`);
  throw new Error(`Could not type into ${label}`);
}

async function fieldValue(ariaLabel) {
  return cdp.evaluate(`(() => {
    const input = document.querySelector('input[aria-label=${JSON.stringify(ariaLabel)}]');
    return input ? input.value : null;
  })()`);
}

async function clickFieldAndType(x, y, ariaLabel, text, label) {
  await mouseClick(x, y);
  await sleep(300);
  const typeChars = async (chars) => {
    for (const ch of chars) {
      await cdp.send('Input.dispatchKeyEvent', {
        type: 'keyDown',
        text: ch,
        key: ch,
        code: '',
        unmodifiedText: ch,
      });
      await cdp.send('Input.dispatchKeyEvent', {
        type: 'keyUp',
        key: ch,
        code: '',
      });
    }
  };
  await typeChars(text);
  // Flutter's hidden input can drop the final character; poll and append the
  // missing suffix until the field holds the full value.
  for (let i = 0; i < 20; i++) {
    await sleep(250);
    const value = await fieldValue(ariaLabel);
    if (value === text) break;
    if (text.startsWith(value) && value.length > 0) {
      await typeChars(text.slice(value.length));
      continue;
    }
    if (i === 19) {
      await dumpSemantics(
        `field ${label} incomplete (got ${JSON.stringify(value)})`,
      );
      throw new Error(
        `Field ${label} incomplete: expected ${JSON.stringify(text)}, got ${JSON.stringify(value)}`,
      );
    }
  }
  await sleep(300);
  const finalValue = await fieldValue(ariaLabel);
  if (finalValue !== text) {
    await dumpSemantics(
      `field ${label} mismatch (got ${JSON.stringify(finalValue)})`,
    );
    throw new Error(
      `Field ${label} mismatch: expected ${JSON.stringify(text)}, got ${JSON.stringify(finalValue)}`,
    );
  }
  return true;
}

async function clearField(x, y, ariaLabel, label) {
  await mouseClick(x, y);
  await sleep(300);
  const backspace = async () => {
    await cdp.send('Input.dispatchKeyEvent', {
      type: 'keyDown',
      key: 'Backspace',
      code: 'Backspace',
      windowsVirtualKeyCode: 8,
    });
    await cdp.send('Input.dispatchKeyEvent', {
      type: 'keyUp',
      key: 'Backspace',
      code: 'Backspace',
      windowsVirtualKeyCode: 8,
    });
  };
  for (let i = 0; i < 80; i++) {
    await backspace();
    await sleep(40);
    const value = await fieldValue(ariaLabel);
    if (value === '') return true;
  }
  const value = await fieldValue(ariaLabel);
  throw new Error(`Could not clear ${label} (value=${JSON.stringify(value)})`);
}

async function focusedInputValue() {
  return cdp.evaluate(`(() => {
    const active = document.activeElement;
    return active && active.tagName === 'INPUT' ? active.value : null;
  })()`);
}

async function dumpSemantics(label) {
  const nodes = await semantics().catch(() => []);
  console.error(
    `[debug ${label}] semantics:\n${JSON.stringify(nodes.slice(0, 50), null, 2)}`,
  );
}

async function signIn() {
  await waitFor(() => findNode('Parent Dashboard'), {label: 'login page'});
  await clickFragment('Parent Dashboard');
  try {
    await waitFor(() => findNode('Private parent access'), {
      label: 'parent sign-in page',
      timeout: 30000,
    });
  } catch (error) {
    await dumpSemantics('parent sign-in timeout');
    throw error;
  }
  await sleep(1200);
  // Flutter web exposes the fields as real inputs with aria-labels; the email
  // row is centered around y=205 and the password row around y=260.
  await clickFieldAndType(200, 205, 'Parent email', EMAIL, 'email');
  await clickFieldAndType(200, 260, 'Password', PASSWORD, 'password');
  await clickFragment('Secure parent sign in');
  // The dashboard mounts only after a successful parent sign-in; the
  // getLinkedChildren call is the reliable backend signal (the Flutter web
  // semantics tree is unreliable across the pushed route).
  await waitFor(
    () =>
      cdp.events.some(
        (e) =>
          e.method === 'Network.requestWillBeSent' &&
          e.params.request.url.includes('getLinkedChildren'),
      ),
    {label: 'getLinkedChildren call', timeout: 45000},
  );
  await sleep(4000);
}

async function similarityToGolden(livePath, goldenName) {
  const liveB64 = fs.readFileSync(livePath).toString('base64');
  const goldenB64 = fs
    .readFileSync(path.join(OUT_DIR, `${goldenName}.png`))
    .toString('base64');
  return cdp.evaluate(`(async () => {
    const load = (b64) => new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = reject;
      img.src = 'data:image/png;base64,' + b64;
    });
    const [a, b] = await Promise.all([
      load(${JSON.stringify(liveB64)}),
      load(${JSON.stringify(goldenB64)}),
    ]);
    const w = 48;
    const h = 200;
    const canvas = document.createElement('canvas');
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext('2d');
    const sample = (image) => {
      ctx.clearRect(0, 0, w, h);
      ctx.drawImage(image, 0, 0, w, h);
      return ctx.getImageData(0, 0, w, h).data;
    };
    const da = sample(a);
    const db = sample(b);
    let sum = 0;
    for (let i = 0; i < da.length; i += 4) {
      const ga = 0.299 * da[i] + 0.587 * da[i + 1] + 0.114 * da[i + 2];
      const gb = 0.299 * db[i] + 0.587 * db[i + 1] + 0.114 * db[i + 2];
      const diff = ga - gb;
      sum += diff * diff;
    }
    return 1 - Math.sqrt(sum / (w * h)) / 255;
  })()`);
}

async function captureAndVerify(name, spec) {
  const shot = await screenshot(`live-${name}.png`);
  const similarity = await similarityToGolden(shot.file, name);
  const text = await pageText();
  const missing = spec.include.filter((entry) => !text.includes(entry));
  const unwanted = spec.exclude.filter((entry) => text.includes(entry));
  return {name, similarity, missing, unwanted, ...shot};
}

async function captureState(name) {
  const spec = STATES[name];
  execFileSync('node', [SEED_SCRIPT, '--state', spec.seed], {
    cwd: WORKTREE,
    stdio: 'pipe',
  });
  await cdp.send('Page.reload', {ignoreCache: true});
  await enableSemantics();
  await signIn();
  const first = await captureAndVerify(name, spec);
  if (first.similarity < 0.7) {
    // Layout mismatch: retake once before judging (the sign-in call itself is
    // proven by getLinkedChildren; this guards a transient paint).
    await sleep(3000);
    const second = await captureAndVerify(name, spec);
    second.retried = true;
    return second;
  }
  return first;
}

async function screenshot(name) {
  const shot = await cdp.send('Page.captureScreenshot', {
    format: 'png',
    captureBeyondViewport: true,
  });
  const file = path.join(OUT_DIR, name);
  fs.writeFileSync(file, Buffer.from(shot.data, 'base64'));
  return {file, bytes: shot.data.length};
}

async function probe() {
  await cdp.send('Page.navigate', {url: APP_URL});
  await enableSemantics();
  const observed = [];
  for (let i = 0; i < 24; i++) {
    const state = await cdp.evaluate(`(() => ({
      title: document.title,
      readyState: document.readyState,
      hasFlutterView: !!document.querySelector('flutter-view'),
      hasSemanticsHost: !!document.querySelector('flt-semantics-host'),
      semanticsCount: document.querySelectorAll('flt-semantics').length,
      bodySnippet: (document.body ? document.body.innerText : '').slice(0, 300),
    }))()`);
    observed.push({
      t: i * 5,
      count: state.semanticsCount,
      hasHost: state.hasSemanticsHost,
      hasView: state.hasFlutterView,
    });
    if (state.semanticsCount > 0) break;
    await sleep(5000);
  }
  const nodes = await semantics();
  const text = await pageText();
  const pageState = await cdp.evaluate(`(() => ({
    title: document.title,
    readyState: document.readyState,
    hasFlutterView: !!document.querySelector('flutter-view'),
    hasSemanticsHost: !!document.querySelector('flt-semantics-host'),
    semanticsCount: document.querySelectorAll('flt-semantics').length,
    placeholderChildren: document.querySelector('flt-semantics-placeholder')
      ? document.querySelector('flt-semantics-placeholder').children.length
      : null,
    accessibilityFeatures:
      window.chrome && window.chrome.accessibilityFeatures
        ? {
            spokenFeedback:
              window.chrome.accessibilityFeatures.spokenFeedback
                ? window.chrome.accessibilityFeatures.spokenFeedback.value
                : null,
            screenReader:
              window.chrome.accessibilityFeatures.screenReader
                ? window.chrome.accessibilityFeatures.screenReader.value
                : null,
          }
        : null,
    bodySnippet: (document.body ? document.body.innerText : '').slice(0, 300),
  }))()`);
  const shot = await cdp.send('Page.captureScreenshot', {
    format: 'png',
    captureBeyondViewport: true,
  });
  fs.writeFileSync(
    path.join(os.tmpdir(), 'u14-probe.png'),
    Buffer.from(shot.data, 'base64'),
  );
  console.log(
    JSON.stringify(
      {
        observed,
        pageState,
        probePng: path.join(os.tmpdir(), 'u14-probe.png'),
        nodes: nodes.slice(0, 80),
        text: text.slice(0, 3000),
      },
      null,
      2,
    ),
  );
}

async function probeSignIn() {
  await cdp.send('Page.navigate', {url: APP_URL});
  await enableSemantics();
  await waitFor(() => findNode('Parent Dashboard'), {label: 'login page'});
  await clickFragment('Parent Dashboard');
  await waitFor(() => findNode('Private parent access'), {
    label: 'parent sign-in page',
    timeout: 30000,
  });
  await sleep(1500);
  const rows = [];
  for (let y = 150; y <= 320; y += 10) {
    await mouseClick(200, y);
    await sleep(250);
    const inputs = await cdp.evaluate(`(() => {
      const list = [...document.querySelectorAll('input')].map((i) => ({
        type: i.type,
        value: i.value,
        aria: i.getAttribute('aria-label'),
        placeholder: i.getAttribute('placeholder'),
        top: Math.round(i.getBoundingClientRect().top),
      }));
      const active = document.activeElement;
      return {
        inputs: list,
        activeIsInput: !!(active && active.tagName === 'INPUT'),
      };
    })()`);
    rows.push({y, ...inputs});
  }
  console.log(JSON.stringify({rows}, null, 2));
}

async function probeAfterSignIn() {
  await cdp.send('Page.navigate', {url: APP_URL});
  await enableSemantics();
  await waitFor(() => findNode('Parent Dashboard'), {label: 'login page'});
  await clickFragment('Parent Dashboard');
  await waitFor(() => findNode('Private parent access'), {
    label: 'parent sign-in page',
    timeout: 30000,
  });
  await sleep(1200);
  await clickFieldAndType(200, 205, 'Parent email', EMAIL, 'email');
  await clickFieldAndType(200, 260, 'Password', PASSWORD, 'password');
  await clickFragment('Secure parent sign in');
  const snapshots = [];
  for (const delay of [5000, 15000, 30000]) {
    await sleep(delay - (snapshots.length ? 0 : 0));
    const text = await pageText();
    const nodes = await semantics();
    snapshots.push({
      delay,
      text: text.slice(0, 2500),
      hasAiman: text.includes('Aiman'),
      hasLearningSnapshot: text.includes('Learning snapshot'),
      hasError: text.includes('The parent account details are incorrect'),
      nodeCount: nodes.length,
    });
  }
  console.log(JSON.stringify({snapshots}, null, 2));
}

async function probeNetwork() {
  await cdp.send('Page.navigate', {url: APP_URL});
  await enableSemantics();
  await waitFor(() => findNode('Parent Dashboard'), {label: 'login page'});
  await clickFragment('Parent Dashboard');
  await waitFor(() => findNode('Private parent access'), {
    label: 'parent sign-in page',
    timeout: 30000,
  });
  await sleep(1200);
  await clickFieldAndType(200, 205, 'Parent email', EMAIL, 'email');
  await clickFieldAndType(200, 260, 'Password', PASSWORD, 'password');
  await clickFragment('Secure parent sign in');
  await sleep(8000);
  const probeShot = await screenshot('probe-network-check.png');
  const consoleLogs = cdp.events
    .filter(
      (e) =>
        e.method === 'Runtime.consoleAPICalled' ||
        e.method === 'Runtime.exceptionThrown' ||
        e.method === 'Log.entryAdded',
    )
    .slice(-25)
    .map((e) => {
      if (e.method === 'Runtime.consoleAPICalled') {
        return {
          type: e.params.type,
          args: e.params.args
            .map((a) => (a.value === undefined ? a.description : a.value))
            .join(' '),
        };
      }
      if (e.method === 'Runtime.exceptionThrown') {
        return {
          exception: e.params.exceptionDetails.exception
            ? e.params.exceptionDetails.exception.description ||
              e.params.exceptionDetails.text
            : e.params.exceptionDetails.text,
        };
      }
      return {log: e.params.entry.text};
    });
  const requests = cdp.events
    .filter(
      (e) =>
        e.method === 'Network.requestWillBeSent' &&
        /(9099|5001|8080)/.test(e.params.request.url),
    )
    .map((e) => ({
      url: e.params.request.url,
      method: e.params.request.method,
      postData: (e.params.request.postData || '').slice(0, 300),
    }));
  const text = await pageText();
  console.log(
    JSON.stringify(
      {
        requests,
        probeShot,
        consoleLogs,
        hasError: text.includes('The parent account details are incorrect'),
        hasDashboard: text.includes('Safe learning updates for Aiman'),
        text: text.slice(0, 1200),
      },
      null,
      2,
    ),
  );
}

async function probePages() {
  await cdp.send('Page.navigate', {url: APP_URL});
  await enableSemantics();
  await waitFor(() => findNode('Parent Dashboard'), {label: 'login page'});
  await sleep(2000);
  const loginShot = await screenshot('probe-login.png');
  await clickFragment('Parent Dashboard');
  await waitFor(() => findNode('Private parent access'), {
    label: 'parent sign-in page',
    timeout: 30000,
  });
  await sleep(2000);
  const parentShot = await screenshot('probe-parent.png');
  await clickFieldAndType(200, 205, 'Parent email', EMAIL, 'email');
  await clickFieldAndType(200, 260, 'Password', PASSWORD, 'password');
  await clickFragment('Secure parent sign in');
  await sleep(8000);
  const dashboardShot = await screenshot('probe-dashboard.png');
  const canvasInfo = await cdp.evaluate(`(() => {
    const view = document.querySelector('flutter-view');
    const root = view ? (view.shadowRoot || view) : null;
    const canvases = root ? root.querySelectorAll('canvas') : [];
    const glass = root ? root.querySelector('flt-glass-pane') : null;
    const resources = performance
      .getEntriesByType('resource')
      .map((e) => e.name)
      .filter((n) => /canvaskit|skwasm|\.wasm/.test(n))
      .slice(0, 10);
    return {
      viewRect: view
        ? {x: view.getBoundingClientRect().x, y: view.getBoundingClientRect().y, w: view.getBoundingClientRect().width, h: view.getBoundingClientRect().height}
        : null,
      hasShadowRoot: !!(view && view.shadowRoot),
      viewHtml: view ? view.innerHTML.slice(0, 400) : null,
      resources,
      flutterCanvasKit: !!window.flutterCanvasKit,
      canvases: [...canvases].map((c) => ({
        w: c.width,
        h: c.height,
        className: c.className,
      })),
      glassRect: glass
        ? {
            w: glass.getBoundingClientRect().width,
            h: glass.getBoundingClientRect().height,
          }
        : null,
      bodyScrollHeight: document.body ? document.body.scrollHeight : null,
    };
  })()`);
  const text = await pageText();
  console.log(
    JSON.stringify(
      {
        loginShot,
        parentShot,
        dashboardShot,
        canvasInfo,
        hasDashboard: text.includes('Safe learning updates for Aiman'),
        hasBack: text.includes('Back'),
      },
      null,
      2,
    ),
  );
}

async function probeRender() {
  await cdp.send('Page.navigate', {url: APP_URL});
  await sleep(20000);
  const info = await cdp.evaluate(`(() => {
    const view = document.querySelector('flutter-view');
    const root = view ? (view.shadowRoot || view) : null;
    const glass = root ? root.querySelector('flt-glass-pane') : null;
    const canvases = glass ? glass.querySelectorAll('canvas') : [];
    return {
      hasView: !!view,
      viewRect: view
        ? {
            w: view.getBoundingClientRect().width,
            h: view.getBoundingClientRect().height,
          }
        : null,
      glassRect: glass
        ? {
            w: glass.getBoundingClientRect().width,
            h: glass.getBoundingClientRect().height,
          }
        : null,
      canvasCount: canvases.length,
      canvases: [...canvases].map((c) => ({w: c.width, h: c.height})),
      bodyText: (document.body ? document.body.innerText : '').slice(0, 200),
    };
  })()`);
  const shot = await screenshot('probe-render.png');
  console.log(JSON.stringify({info, shot}, null, 2));
}

let chrome;
let cdp;

(async () => {
  const args = process.argv.slice(2);
  fs.mkdirSync(OUT_DIR, {recursive: true});
  const userDataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'u14-chrome-'));
  chrome = spawn(
    CHROME,
    [
      '--no-sandbox',
      '--disable-dev-shm-usage',
      '--force-renderer-accessibility',
      '--enable-accessibility',
      '--window-size=430,1800',
      '--force-device-scale-factor=1',
      `--remote-debugging-port=${CDP_PORT}`,
      `--user-data-dir=${userDataDir}`,
      'about:blank',
    ],
    {stdio: 'ignore'},
  );

  let pageUrl = null;
  for (let i = 0; i < 60; i++) {
    try {
      const response = await fetch(
        `http://127.0.0.1:${CDP_PORT}/json/new?url=${encodeURIComponent('about:blank')}`,
        {method: 'PUT'},
      );
      if (response.ok) {
        pageUrl = (await response.json()).webSocketDebuggerUrl;
        break;
      }
    } catch (_) {
      // Chrome still starting
    }
    await sleep(300);
  }
  if (!pageUrl) throw new Error('Chrome DevTools endpoint did not come up');

  cdp = await Cdp.connect(pageUrl);
  await cdp.send('Page.enable');
  await cdp.send('Runtime.enable');
  await cdp.send('Accessibility.enable');
  await cdp.send('Network.enable');
  if (!args.includes('--probe-render')) {
    await cdp.send('Network.setUserAgentOverride', {
      userAgent: FIREFOX_UA,
      platform: 'Win32',
    });
    await cdp.send('Emulation.setDeviceMetricsOverride', {
      width: 430,
      height: 1800,
      deviceScaleFactor: 1,
      mobile: true,
    });
  }

  if (args.includes('--probe')) {
    await probe();
    return;
  }
  if (args.includes('--probe-signin')) {
    await probeSignIn();
    return;
  }
  if (args.includes('--probe-after-signin')) {
    await probeAfterSignIn();
    return;
  }
  if (args.includes('--probe-network')) {
    await probeNetwork();
    return;
  }
  if (args.includes('--probe-pages')) {
    await probePages();
    return;
  }
  if (args.includes('--probe-render')) {
    await probeRender();
    return;
  }

  await cdp.send('Page.navigate', {url: APP_URL});
  await enableSemantics();
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
        appUrl: APP_URL,
        parentEmail: EMAIL,
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
}).finally(() => {
  if (chrome && !chrome.killed) chrome.kill();
});
