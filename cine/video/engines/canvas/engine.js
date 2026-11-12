import {Output, Mp4OutputFormat, BufferTarget, CanvasSource, Quality} from './vendor/mediabunny.js';

const W = 1920;
const H = 1080;
const canvas = document.getElementById('c');
const g = canvas.getContext('2d');
const images = new Map();

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const im = new Image();
    im.onload = () => {
      images.set(src, im);
      resolve(im);
    };
    im.onerror = () => reject(new Error(`图片加载失败：${src}`));
    im.src = src;
  });
}

function b64(bytes) {
  let s = '';
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    s += String.fromCharCode(...bytes.subarray(i, i + chunk));
  }
  return btoa(s);
}

export async function boot() {
  const q = new URLSearchParams(location.search);
  const filmUrl = q.get('film');
  if (!filmUrl) throw new Error('缺少 ?film=...');

  const film = await import(filmUrl);
  await Promise.all((film.images || []).map(loadImage));

  const c = {
    canvas,
    ctx: g,
    W,
    H,
    t: 0,
    img: (src) => images.get(src),
  };
  const shots = await film.build(c);
  window.__filmCanvas = {duration: film.duration, fps: film.fps, shots: shots.length};

  window.renderFilm = async (opts = {}) => {
    const fps = opts.fps || film.fps || 30;
    const duration = opts.duration || film.duration;
    const output = new Output({
      format: new Mp4OutputFormat(),
      target: new BufferTarget(),
    });
    const source = new CanvasSource(canvas, {
      codec: 'avc',
      quality: new Quality(opts.quality || 20_000_000),
      hardwareAcceleration: opts.hardwareAcceleration || 'no-preference',
    });
    output.addVideoTrack(source, {frameRate: fps});
    await output.start();

    const n = Math.round(duration * fps);
    for (let i = 0; i < n; i++) {
      const t = i / fps;
      c.t = t;
      g.clearRect(0, 0, W, H);
      const shot = shots.find((s) => t >= s.from && t < s.to) || shots[shots.length - 1];
      shot.draw(t, c);
      await source.add(t, 1 / fps);
    }
    await output.finalize();
    return b64(new Uint8Array(output.target.buffer));
  };

  window.ready = true;
}
