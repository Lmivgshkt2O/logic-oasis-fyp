/* Quick pixel-analysis helper: reports dimensions and hue-band coverage for a
 * list of PNGs so the live captures can be judged without visual inspection.
 */
const {spawn} = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const CHROME =
  process.env.CHROME_PATH ||
  'C:\\Users\\zyonn\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe';
const CDP_PORT = 9400 + (process.pid % 300);

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

class Cdp {
  constructor(ws) {
    this.ws = ws;
    this.id = 0;
    this.pending = new Map();
  }
  static async connect(url) {
    const ws = new WebSocket(url);
    await new Promise((resolve, reject) => {
      ws.onopen = resolve;
      ws.onerror = () => reject(new Error('ws open failed'));
    });
    const cdp = new Cdp(ws);
    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (!message.id || !cdp.pending.has(message.id)) return;
      const {resolve, reject} = cdp.pending.get(message.id);
      cdp.pending.delete(message.id);
      message.error
        ? reject(new Error(message.error.message))
        : resolve(message.result);
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
      throw new Error(JSON.stringify(result.exceptionDetails.exception));
    }
    return result.result.value;
  }
}

(async () => {
  const files = process.argv.slice(2);
  const similarityMode = files[0] === '--similarity';
  if (similarityMode) files.shift();
  const userDataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'u14-analyze-'));
  const chrome = spawn(
    CHROME,
    [
      '--headless=new',
      '--disable-gpu',
      '--no-sandbox',
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
    } catch (_) {}
    await sleep(300);
  }
  if (!pageUrl) throw new Error('chrome did not start');
  const cdp = await Cdp.connect(pageUrl);
  await cdp.send('Runtime.enable');
  const encoded = files.map((file) => ({
    name: path.basename(file),
    b64: fs.readFileSync(file).toString('base64'),
  }));
  const result = await cdp.evaluate(`(async () => {
    const load = (b64) => new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = reject;
      img.src = 'data:image/png;base64,' + b64;
    });
    if (${JSON.stringify(similarityMode)}) {
      const encoded = ${JSON.stringify(encoded)};
      const w = 48;
      const h = 200;
      const canvas = document.createElement('canvas');
      canvas.width = w;
      canvas.height = h;
      const ctx = canvas.getContext('2d');
      const sample = (image) => {
        ctx.clearRect(0, 0, w, h);
        const scale = Math.min(w / image.naturalWidth, h / image.naturalHeight);
        const dw = image.naturalWidth * scale;
        const dh = image.naturalHeight * scale;
        ctx.drawImage(image, (w - dw) / 2, (h - dh) / 2, dw, dh);
        return ctx.getImageData(0, 0, w, h).data;
      };
      const grayscale = (data) => {
        const out = new Float32Array(w * h);
        for (let i = 0, j = 0; i < data.length; i += 4, j++) {
          out[j] = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
        }
        return out;
      };
      const out = [];
      for (let i = 0; i < encoded.length; i += 2) {
        const a = grayscale(sample(await load(encoded[i].b64)));
        const b = grayscale(sample(await load(encoded[i + 1].b64)));
        let sum = 0;
        for (let j = 0; j < a.length; j++) {
          const d = a[j] - b[j];
          sum += d * d;
        }
        out.push({
          a: encoded[i].name,
          b: encoded[i + 1].name,
          similarity: +(1 - Math.sqrt(sum / a.length) / 255).toFixed(3),
        });
      }
      return out;
    }
    const out = [];
    for (const entry of ${JSON.stringify(encoded)}) {
      const img = await load(entry.b64);
      const w = 120;
      const h = Math.max(1, Math.round((img.naturalHeight / img.naturalWidth) * w));
      const canvas = document.createElement('canvas');
      canvas.width = w;
      canvas.height = h;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(img, 0, 0, w, h);
      const data = ctx.getImageData(0, 0, w, h).data;
      let warm = 0;
      let green = 0;
      let blue = 0;
      let dark = 0;
      const total = (w * h);
      for (let i = 0; i < data.length; i += 4) {
        const r = data[i];
        const g = data[i + 1];
        const b = data[i + 2];
        const max = Math.max(r, g, b);
        const min = Math.min(r, g, b);
        const lightness = (max + min) / 2;
        if (lightness < 0.45 * 255) { dark++; continue; }
        if (max - min < 24) continue;
        let hue = 0;
        if (max === r) hue = ((g - b) / (max - min)) % 6;
        else if (max === g) hue = (b - r) / (max - min) + 2;
        else hue = (r - g) / (max - min) + 4;
        hue = (hue * 60 + 360) % 360;
        const saturation = max === 0 ? 0 : (max - min) / max;
        if (saturation < 0.2) continue;
        if (hue < 50) warm++;
        else if (hue < 170) green++;
        else if (hue < 250) blue++;
      }
      out.push({
        name: entry.name,
        natural: img.naturalWidth + 'x' + img.naturalHeight,
        warm: +(warm / total).toFixed(4),
        green: +(green / total).toFixed(4),
        blue: +(blue / total).toFixed(4),
        dark: +(dark / total).toFixed(4),
      });
    }
    return out;
  })()`);
  console.log(JSON.stringify(result, null, 2));
  chrome.kill();
})().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
