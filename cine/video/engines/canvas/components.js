// Canvas 快速通道组件：全部是「给定局部进度 u，画一帧」的纯函数。
// film.canvas.js 里：bg(c) → title/keyword/counter/bars/plate → foot/chapter/progress
const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const ease = (x) => {
  x = clamp(x);
  return x * x * (3 - 2 * x);
};
const fade = (u, fin = 0.12, fout = 0.10) => clamp(Math.min(u / fin, (1 - u) / fout));

export function bg(c, {warm = 0} = {}) {
  const g = c.ctx;
  const t = c.t || 0;
  const gr = g.createLinearGradient(0, 0, 0, c.H);
  gr.addColorStop(0, `hsl(${210 - warm * 170}, ${46 + warm * 20}%, ${18 + warm * 2}%)`);
  gr.addColorStop(0.55, `hsl(${214 - warm * 180}, ${42 + warm * 18}%, ${10 + warm * 2}%)`);
  gr.addColorStop(1, `hsl(${220 - warm * 195}, 38%, 5%)`);
  g.fillStyle = gr;
  g.fillRect(0, 0, c.W, c.H);

  const gx = 1450 + Math.sin(t * 0.22) * 120;
  const gy = 300 + Math.cos(t * 0.18) * 70;
  const glow = g.createRadialGradient(gx, gy, 0, gx, gy, 620);
  glow.addColorStop(0, `hsla(${40 + warm * 8}, 80%, 60%, ${0.16 + warm * 0.2})`);
  glow.addColorStop(1, 'rgba(0,0,0,0)');
  g.fillStyle = glow;
  g.fillRect(0, 0, c.W, c.H);

  for (let k = 0; k < 46; k++) {
    const x = ((k * 137 + t * (8 + (k % 4) * 3)) % (c.W + 160)) - 80;
    const y = (k * 89 + Math.sin(t * 0.5 + k) * 20) % c.H;
    g.globalAlpha = 0.12 + (k % 5) * 0.035;
    g.fillStyle = k % 7 === 0 ? '#e0b060' : '#9fc6ff';
    g.beginPath();
    g.arc(x, y, 1 + (k % 3), 0, Math.PI * 2);
    g.fill();
  }
  g.globalAlpha = 1;
}

function titleBlock(c, text, sub, u, size = 92) {
  const g = c.ctx;
  const a = fade(u);
  const slide = (1 - ease(u / 0.2)) * 26;
  const x = 150 - slide;
  const y = 430;

  g.globalAlpha = a;
  g.fillStyle = '#f4f0e8';
  g.font = `700 ${size}px "Microsoft YaHei", "Noto Sans SC", sans-serif`;
  g.textAlign = 'left';
  g.textBaseline = 'alphabetic';
  g.fillText(text, x, y);

  g.globalAlpha = a * 0.72;
  g.fillStyle = '#9fb3c8';
  g.font = '400 34px "Microsoft YaHei", "Noto Sans SC", sans-serif';
  g.fillText(sub, x, y + 76);

  g.globalAlpha = a * 0.9;
  g.fillStyle = '#e0b060';
  g.fillRect(x, y + 112, ease(u / 0.8) * 620, 4);
  g.globalAlpha = 1;
}

export function title(c, {text, sub, u}) {
  titleBlock(c, text, sub, u, 92);
}

export function keyword(c, {text, sub, u}) {
  titleBlock(c, text, sub, u, 84);
}

export function counter(c, {value, from = 0, label, sub, u, suffix = '', decimals = 1}) {
  const g = c.ctx;
  const a = fade(u);
  const k = ease(u / 0.7);
  const v = from + (value - from) * k;
  const x = 150;
  const y = 520;

  g.globalAlpha = a;
  g.fillStyle = '#e0b060';
  g.font = '700 190px "Geist", "Microsoft YaHei", sans-serif';
  g.textAlign = 'left';
  g.fillText(v.toFixed(decimals) + suffix, x, y);

  g.globalAlpha = a * 0.85;
  g.fillStyle = '#f4f0e8';
  g.font = '600 42px "Microsoft YaHei", sans-serif';
  g.fillText(label, x, y + 70);

  g.globalAlpha = a * 0.6;
  g.fillStyle = '#9fb3c8';
  g.font = '400 28px "Microsoft YaHei", sans-serif';
  g.fillText(sub, x, y + 116);
  g.globalAlpha = 1;
}

export function bars(c, {items, title, u, max = null}) {
  const g = c.ctx;
  const a = fade(u);
  const m = max || Math.max(...items.map((x) => x.value));
  const x0 = 650;
  const x1 = 1700;
  const y0 = 400;

  g.globalAlpha = a * 0.9;
  g.fillStyle = '#f4f0e8';
  g.font = '600 46px "Microsoft YaHei", sans-serif';
  g.textAlign = 'left';
  g.fillText(title, 150, 300);

  items.forEach((it, i) => {
    const y = y0 + i * 150;
    const w = ease(u / 0.75) * (x1 - x0) * (it.value / m);
    g.globalAlpha = a * 0.85;
    g.fillStyle = '#c9d6e6';
    g.font = '500 30px "Microsoft YaHei", sans-serif';
    g.fillText(it.label, 150, y + 38);

    g.globalAlpha = a * 0.14;
    g.fillStyle = '#ffffff';
    g.fillRect(x0, y, x1 - x0, 54);

    g.globalAlpha = a * 0.92;
    g.fillStyle = it.color;
    g.fillRect(x0, y, w, 54);

    g.globalAlpha = a * 0.9;
    g.fillStyle = '#f4f0e8';
    g.font = '700 34px "Geist", "Microsoft YaHei", sans-serif';
    g.fillText(it.value.toFixed(1), x0 + w + 18, y + 40);
  });
  g.globalAlpha = 1;
}

export function plate(c, {src, u, zoom = [1.04, 1.14], shade = 0.48, tag = 'AI 示意图'}) {
  const g = c.ctx;
  const im = c.img(src);
  const a = fade(u, 0.15, 0.12);
  g.globalAlpha = a;
  if (im) {
    const s = zoom[0] + (zoom[1] - zoom[0]) * ease(u);
    const w = c.W * s;
    const h = c.H * s;
    const dx = (c.W - w) / 2;
    const dy = (c.H - h) / 2;
    g.drawImage(im, dx, dy, w, h);
  } else {
    g.fillStyle = '#12212f';
    g.fillRect(0, 0, c.W, c.H);
  }
  const sh = g.createLinearGradient(0, 0, c.W, 0);
  sh.addColorStop(0, `rgba(5,8,12,${shade})`);
  sh.addColorStop(0.55, `rgba(5,8,12,${shade * 0.35})`);
  sh.addColorStop(1, `rgba(5,8,12,${shade * 0.7})`);
  g.fillStyle = sh;
  g.fillRect(0, 0, c.W, c.H);

  if (tag) {
    g.globalAlpha = a * 0.55;
    g.fillStyle = '#000';
    g.fillRect(c.W - 190, 40, 150, 34);
    g.fillStyle = '#c9d6e6';
    g.font = '500 18px "Microsoft YaHei", sans-serif';
    g.textAlign = 'left';
    g.fillText(tag, c.W - 178, 63);
    g.globalAlpha = 1;
  }
}

export function spectrum(c, {u}) {
  const g = c.ctx;
  const a = fade(u);
  const colors = ['#ff5b4a', '#ff9b3d', '#ffd84a', '#6fe08a', '#4bb8ff', '#5b6bff', '#b06bff'];
  const baseY = 760;
  const x0 = 1200;
  for (let i = 0; i < colors.length; i++) {
    const h = 100 + Math.sin((c.t || 0) * 2.2 + i * 0.7) * 40 + i * 10;
    g.globalAlpha = a * 0.9;
    g.fillStyle = colors[i];
    g.fillRect(x0 + i * 62, baseY - h, 42, h);
  }
  g.globalAlpha = 1;
}

export function waves(c, {u}) {
  const g = c.ctx;
  const a = fade(u);
  for (let k = 0; k < 5; k++) {
    g.beginPath();
    for (let x = 0; x <= c.W; x += 8) {
      const y = 760 + k * 34 + Math.sin(x * 0.012 + (c.t || 0) * (1.4 + k * 0.2) + k) * (20 + k * 6);
      if (x === 0) g.moveTo(x, y);
      else g.lineTo(x, y);
    }
    g.globalAlpha = a * (0.18 + k * 0.1);
    g.strokeStyle = k % 2 ? '#e0b060' : '#69b7ff';
    g.lineWidth = 2;
    g.stroke();
  }
  g.globalAlpha = 1;
}

export function sunset(c, {u, warm = 1}) {
  const g = c.ctx;
  const a = fade(u);
  const sunY = 860 - warm * 80;
  const sunX = 1500;
  const sun = g.createRadialGradient(sunX, sunY, 0, sunX, sunY, 260);
  sun.addColorStop(0, `rgba(255, ${190 - warm * 40}, 90, ${0.95 * a})`);
  sun.addColorStop(0.25, `rgba(255, 120, 50, ${0.7 * a})`);
  sun.addColorStop(1, 'rgba(255,80,30,0)');
  g.fillStyle = sun;
  g.beginPath();
  g.arc(sunX, sunY, 260, 0, Math.PI * 2);
  g.fill();

  g.globalAlpha = a * 0.35;
  g.strokeStyle = '#ff9b5a';
  g.lineWidth = 2;
  for (let k = 0; k < 7; k++) {
    g.beginPath();
    g.moveTo(0, 820 + k * 26);
    g.lineTo(c.W, 760 + k * 26);
    g.stroke();
  }
  g.globalAlpha = 1;
}

export function foot(c, {text}) {
  const g = c.ctx;
  g.globalAlpha = 0.68;
  g.fillStyle = '#7590a8';
  g.font = '400 22px "Microsoft YaHei", sans-serif';
  g.textAlign = 'left';
  g.fillText(text, 80, 1020);
  g.globalAlpha = 1;
}

export function chapter(c, {index, total}) {
  const g = c.ctx;
  g.globalAlpha = 0.7;
  g.fillStyle = '#c9d6e6';
  g.font = '600 24px "Microsoft YaHei", sans-serif';
  g.textAlign = 'left';
  g.fillText('VIBE 知识大赏 · BGM ONLY', 80, 72);
  g.textAlign = 'right';
  g.fillStyle = '#8fa6bd';
  g.fillText(`${String(index).padStart(2, '0')} / ${String(total).padStart(2, '0')}`, 1840, 72);
  g.globalAlpha = 1;
}

export function progress(c, {t, duration}) {
  const g = c.ctx;
  g.fillStyle = 'rgba(255,255,255,0.12)';
  g.fillRect(0, c.H - 8, c.W, 4);
  g.fillStyle = '#e0b060';
  g.fillRect(0, c.H - 8, c.W * clamp(t / duration), 4);
}
