// poetry 引擎：书封决定画面 + 代码排版诗句 + BGM。
//
// 背景、书封、雾、光斑、浮尘全部是 DOM/CSS；文字用系统字体渲染，始终锐利。
// 参数全部来自 lessons/<id>/poem.json：
//   const poem = await (await fetch(new URL("./poem.json", import.meta.url))).json();
//   export const {...} = createPoetryFilm(poem, import.meta.url);
import { clamp, el } from "./util.js";

const FONTS = {
  kai: "font-family:'KaiTi','STKaiti','楷体','Kaiti SC','Noto Serif SC','Songti SC',serif;",
  song: "font-family:'Noto Serif SC','Songti SC','STSong','SimSun',serif;",
  sans: "font-family:'NotoSC','Microsoft YaHei',sans-serif;",
};

// 调色板：一个名字定下一整场的冷暖、光晕、字色。
const PALETTES = {
  jade: {
    base: "#050908",
    tint: "linear-gradient(90deg,rgba(3,6,8,.86),rgba(3,6,8,.16) 46%,rgba(3,6,8,.68))",
    radial: "rgba(96,168,144,.17)",
    mistA: "rgba(96,172,146,.16)",
    mistB: "rgba(186,166,124,.1)",
    bokeh: "rgba(150,214,196,.5)",
    dustCool: "#a8cec6",
    dustWarm: "#e2b464",
    halo: "rgba(126,204,172,.30)",
    text: "#F7F0E2",
    credit: "#DECBA6",
    sourceColor: "rgba(196,180,150,.72)",
    headerColor: "rgba(226,178,98,.7)",
    tab: "rgba(220,206,176,.78)",
  },
  ember: {
    base: "#0A0605",
    tint: "linear-gradient(90deg,rgba(10,5,4,.9),rgba(10,5,4,.22) 46%,rgba(10,5,4,.82))",
    radial: "rgba(230,124,66,.2)",
    mistA: "rgba(232,128,70,.16)",
    mistB: "rgba(178,150,120,.11)",
    bokeh: "rgba(255,176,120,.5)",
    dustCool: "#f0c9a8",
    dustWarm: "#ffd48a",
    halo: "rgba(255,152,92,.28)",
    text: "#FBF1E2",
    credit: "#EBCB9E",
    sourceColor: "rgba(214,190,160,.72)",
    headerColor: "rgba(246,190,120,.72)",
    tab: "rgba(232,206,170,.78)",
  },
  moon: {
    base: "#04070E",
    tint: "linear-gradient(90deg,rgba(4,7,14,.88),rgba(4,7,14,.18) 46%,rgba(4,7,14,.72))",
    radial: "rgba(120,150,210,.17)",
    mistA: "rgba(120,150,210,.15)",
    mistB: "rgba(200,200,220,.09)",
    bokeh: "rgba(160,190,255,.5)",
    dustCool: "#b8c8f0",
    dustWarm: "#e8d8a8",
    halo: "rgba(130,165,235,.3)",
    text: "#F4F2EA",
    credit: "#D6CCB4",
    sourceColor: "rgba(190,190,180,.72)",
    headerColor: "rgba(180,200,240,.7)",
    tab: "rgba(210,215,230,.78)",
  },
  ink: {
    base: "#0B0B0A",
    tint: "linear-gradient(90deg,rgba(8,8,7,.9),rgba(8,8,7,.2) 46%,rgba(8,8,7,.72))",
    radial: "rgba(120,120,110,.14)",
    mistA: "rgba(150,150,140,.12)",
    mistB: "rgba(120,110,95,.1)",
    bokeh: "rgba(200,198,180,.4)",
    dustCool: "#cfcfc4",
    dustWarm: "#d8c49a",
    halo: "rgba(200,198,180,.24)",
    text: "#F2EFE6",
    credit: "#CFC4AC",
    sourceColor: "rgba(180,175,160,.7)",
    headerColor: "rgba(200,195,175,.68)",
    tab: "rgba(215,210,195,.75)",
  },
};

const PAL_KEYS = Object.keys(PALETTES.jade);

// 特效默认值：数量 × 不透明度倍率。
const FX = {
  bokeh: 8, bokeh_opacity: 1, bokeh_size: 1, bokeh_rise: 1,
  dust: 46, dust_opacity: 1, dust_size: 1, dust_glow: 1,
  mist: 1, mist_speed: 1,
  grain: 0.04,
  vignette: 0.58,
  halo: 1, sweep: 1,
  zoom: 0.055, drift: 26,
  text_glow: 1,
};

// 一场里的时间点（场景本地秒）：先图，后字。
const GAP = {
  image_in: 1.3,
  text1: 2.1, text2: 2.9,
  credit: 4.3,
  text_dur: 1.2, credit_dur: 1.1,
  rise: 14,
};

const BOOK = { x: 132, y: 148, w: 430, h: 606, tilt: -1.8 };

const smooth = (x) => { x = clamp(x); return x * x * (3 - 2 * x); };

export function createPoetryFilm(cfg, baseUrl) {
  const A = (f) => new URL(`./assets/${f}`, baseUrl).href;
  const P = (f) => decodeURIComponent(new URL(`./assets/${f}`, baseUrl).pathname).slice(1);

  const FONT = FONTS[cfg.font || "kai"] || FONTS.kai;
  const SCENE = Number(cfg.scene_seconds ?? 15);
  const TAIL = Number(cfg.tail ?? 0.3);
  const GLOBAL_GAP = { ...GAP, ...(cfg.gap || {}) };
  const GLOBAL_FX = { ...FX, ...(cfg.effects || {}) };
  // credit_size 留空就按字号比例跟随主句，避免小字场景里署名反而比正文大
  const TYPE = { size: 70, credit_size: 0, credit_ratio: 0.6, source_size: 19, tracking: 4, footer_size: 18, ...(cfg.type || {}) };
  const HEADER_LEFT = cfg.header_left ?? "LITERATURE";
  const music = [];

  const scenes = (cfg.scenes || []).map((sc) => {
    const pal = { ...(PALETTES[sc.palette || cfg.palette || "jade"] || PALETTES.jade) };
    for (const k of PAL_KEYS) if (sc[k] !== undefined) pal[k] = sc[k];
    return {
      sc, pal,
      fx: { ...GLOBAL_FX, ...(sc.effects || {}) },
      gap: { ...GLOBAL_GAP, ...(sc.gap || {}) },
      book: { ...BOOK, ...(cfg.book || {}), ...(sc.book || {}) },
    };
  });

  let cursor = 0;
  for (const s of scenes) {
    s.sec = Number(s.sc.seconds ?? SCENE);
    s.from = cursor;
    s.to = cursor + s.sec;
    cursor = s.to;
  }
  const END = cursor;

  function makeScene(s) {
    const { pal, fx, gap, book, sc } = s;
    const cover = A(sc.cover);
    const trans = Number(sc.transition ?? cfg.transition ?? 0.95);
    const bgFilter = `blur(${Number(sc.blur ?? 7)}px) saturate(${Number(sc.saturate ?? 0.95)}) brightness(${Number(sc.brightness ?? 0.5)})`;

    return {
      from: s.from,
      to: s.to,
      build(root) {
        const shot = el(root, "shot");
        el(shot, "abs", `inset:0;background:${pal.base};`);

        // 画面层整体淡入，诗句在层外，等画面落定再出
        const stage = el(shot, "abs", "inset:0;opacity:0;");

        const bg = el(stage, "abs", `inset:-6%;background-position:center;background-size:cover;filter:${bgFilter};transform:scale(1.10);will-change:transform;`);
        bg.style.backgroundImage = `url("${cover}")`;

        el(stage, "abs", `inset:0;background:${pal.tint};`);
        el(stage, "abs", `inset:0;background:radial-gradient(ellipse at 40% 46%,${pal.radial},transparent 42%,rgba(0,0,0,.5) 100%);`);

        // 雾
        const mist1 = el(stage, "abs", `left:-22%;top:16%;width:150%;height:48%;background:radial-gradient(ellipse at 50% 50%,${pal.mistA},transparent 68%);opacity:${(1 * fx.mist).toFixed(3)};pointer-events:none;`);
        const mist2 = el(stage, "abs", `left:-30%;top:50%;width:170%;height:40%;background:radial-gradient(ellipse at 50% 50%,${pal.mistB},transparent 70%);opacity:${(1 * fx.mist).toFixed(3)};pointer-events:none;`);
        const mist3 = el(stage, "abs", `left:-10%;top:66%;width:130%;height:38%;background:radial-gradient(ellipse at 50% 50%,${pal.mistA},transparent 72%);opacity:${(0.7 * fx.mist).toFixed(3)};pointer-events:none;`);

        // 虚焦光斑
        const bokeh = [...Array(Math.max(0, Math.round(fx.bokeh)))].map((_, i) => {
          const d = (34 + (i % 4) * 18) * fx.bokeh_size;
          const n = el(stage, "abs",
            `left:${(i * 263) % 1880}px;top:${(i * 149) % 1000}px;width:${d}px;height:${d}px;border-radius:50%;` +
            `background:radial-gradient(circle,${pal.bokeh} 0%,transparent 68%);filter:blur(7px);` +
            `opacity:${((0.35 + (i % 3) * 0.12) * fx.bokeh_opacity).toFixed(2)};pointer-events:none;`);
          return { n, phase: i * 1.7, rise: (8 + (i % 4) * 5) * fx.bokeh_rise };
        });

        // 浮尘
        const dust = [...Array(Math.max(0, Math.round(fx.dust)))].map((_, i) => {
          const d = (1.4 + (i % 4) * 0.9) * fx.dust_size;
          const col = i % 7 === 0 ? pal.dustWarm : pal.dustCool;
          const n = el(stage, "abs",
            `left:${(i * 137) % 1920}px;top:${(i * 83) % 1080}px;width:${d.toFixed(1)}px;height:${d.toFixed(1)}px;border-radius:50%;` +
            `background:${col};box-shadow:0 0 ${((3 + (i % 3) * 2) * fx.dust_glow).toFixed(1)}px ${col};` +
            `opacity:${((0.16 + (i % 5) * 0.05) * fx.dust_opacity).toFixed(3)};pointer-events:none;`);
          return { n, phase: i * 0.37, speed: 5 + (i % 5) * 2 };
        });

        // 书封实体
        const bookWrap = el(stage, "abs", `left:${book.x}px;top:${book.y}px;width:${book.w}px;height:${book.h}px;transform:rotate(${book.tilt}deg);will-change:transform;`);
        const halo = el(bookWrap, "abs", `inset:-34px;background:radial-gradient(ellipse at 50% 50%,${pal.halo},transparent 70%);filter:blur(26px);`);
        const bookEl = el(bookWrap, "abs", "inset:0;background-position:center;background-size:cover;box-shadow:26px 36px 76px rgba(0,0,0,.7),0 0 0 9px rgba(246,240,228,.075);");
        bookEl.style.backgroundImage = `url("${cover}")`;
        el(bookWrap, "abs", "left:0;top:0;width:16px;height:100%;background:linear-gradient(90deg,rgba(0,0,0,.42),rgba(0,0,0,0));");
        el(bookWrap, "abs", `left:-14px;top:-12px;width:116px;height:26px;background:${pal.tab};transform:rotate(-5deg);box-shadow:0 3px 10px rgba(0,0,0,.2);opacity:.85;`);
        const sweep = el(bookEl, "abs", `left:-60%;top:-20%;width:55%;height:140%;background:linear-gradient(90deg,transparent,rgba(255,255,255,.20),transparent);transform:rotate(14deg);mix-blend-mode:screen;opacity:${(0.18 * fx.sweep).toFixed(3)};`);

        // 角标
        el(stage, "abs mono", "left:96px;top:78px;font-size:17px;letter-spacing:7px;color:rgba(244,240,232,.52);", HEADER_LEFT);
        el(stage, "abs mono", `right:96px;top:80px;font-size:15px;letter-spacing:4px;color:${pal.headerColor};`, sc.header || "");
        el(stage, "abs mono", `left:96px;bottom:44px;font-size:${TYPE.footer_size}px;letter-spacing:2.5px;color:rgba(244,240,232,.46);`, sc.footer || "");

        const grain = el(stage, "abs", `inset:0;background-image:url("/resources/images/noise.png");background-size:512px 512px;opacity:${Number(fx.grain).toFixed(3)};mix-blend-mode:overlay;pointer-events:none;`);
        el(stage, "abs", `inset:0;background:radial-gradient(ellipse at 50% 46%,transparent 36%,rgba(0,0,0,${clamp(fx.vignette, 0, 1)}) 100%);pointer-events:none;`);

        // 诗句：支持任意行数，逐行错开淡入
        const lines = (sc.lines && sc.lines.length ? sc.lines : [sc.line1, sc.line2]).filter(Boolean);
        const tSize = Number((sc.type && sc.type.size) ?? TYPE.size);
        const tTrack = Number((sc.type && sc.type.tracking) ?? TYPE.tracking);
        const cSize = Number((sc.type && sc.type.credit_size) ?? (TYPE.credit_size || Math.round(tSize * TYPE.credit_ratio)));
        const sSize = Number((sc.type && sc.type.source_size) ?? TYPE.source_size);
        const lineH = tSize * 1.9;
        const top = 470 - ((lines.length - 1) * lineH) / 2;
        const textCss = `left:760px;width:1080px;${FONT}font-size:${tSize}px;line-height:1.9;letter-spacing:${tTrack}px;color:${pal.text};text-shadow:0 3px 28px rgba(0,0,0,.8),0 0 20px rgba(255,236,200,${(0.12 * fx.text_glow).toFixed(3)});opacity:0;`;
        const lineNodes = lines.map((txt, i) =>
          el(shot, "abs", `top:${(top + i * lineH).toFixed(0)}px;${textCss}`, txt));
        const creditTop = top + lines.length * lineH + 38;
        const credit = el(shot, "abs", `left:764px;top:${creditTop.toFixed(0)}px;${FONT}font-size:${cSize}px;letter-spacing:3px;color:${pal.credit};opacity:0;`, sc.credit || "");
        const source = el(shot, "abs", `left:766px;top:${(creditTop + cSize * 1.55).toFixed(0)}px;${FONT}font-size:${sSize}px;letter-spacing:2px;color:${pal.sourceColor};opacity:0;`, sc.source || "");

        const veil = el(shot, "abs", "inset:0;background:#04060A;opacity:0;pointer-events:none;");

        return { s: shot, stage, bg, mist1, mist2, mist3, bokeh, dust, bookWrap, halo, sweep, grain, lines: lineNodes, credit, source, veil };
      },
      render(t, u) {
        const tl = t - s.from;
        const p = clamp(tl / s.sec);

        u.stage.style.opacity = smooth(tl / Math.max(0.01, gap.image_in)).toFixed(3);
        u.bg.style.transform = `scale(${((sc.flip ? -1 : 1) * (1.10 + p * fx.zoom)).toFixed(4)},${(1.10 + p * fx.zoom).toFixed(4)}) translateX(${(-16 + p * fx.drift).toFixed(1)}px) translateY(${(p * -8).toFixed(1)}px)`;
        u.bookWrap.style.transform = `rotate(${book.tilt}deg) translateY(${(Math.sin(tl * 0.5) * 4).toFixed(1)}px)`;
        u.halo.style.opacity = ((0.72 + Math.sin(tl * 0.42) * 0.16) * fx.halo).toFixed(3);
        u.sweep.style.transform = `translateX(${(60 + p * 200).toFixed(1)}%) rotate(14deg)`;
        u.grain.style.backgroundPosition = `${Math.floor(tl * 37) % 512}px ${Math.floor(tl * 29) % 512}px`;

        u.mist1.style.transform = `translateX(${(Math.sin(tl * 0.13 * fx.mist_speed) * 96).toFixed(1)}px)`;
        u.mist2.style.transform = `translateX(${(Math.cos(tl * 0.1 * fx.mist_speed) * 78).toFixed(1)}px)`;
        u.mist3.style.transform = `translateX(${(Math.sin(tl * 0.08 * fx.mist_speed + 1.7) * 64).toFixed(1)}px)`;

        u.bokeh.forEach(({ n, phase, rise }) => {
          const x = (parseFloat(n.style.left) + Math.sin(tl * 0.19 + phase) * 46) % 1980;
          const y = (parseFloat(n.style.top) - tl * rise + Math.sin(tl * 0.13 + phase) * 12) % 1120;
          n.style.transform = `translate(${(x - parseFloat(n.style.left)).toFixed(1)}px,${(y - parseFloat(n.style.top)).toFixed(1)}px)`;
        });
        u.dust.forEach(({ n, phase, speed }) => {
          const x = (parseFloat(n.style.left) + tl * speed) % 1980;
          const y = (parseFloat(n.style.top) + Math.sin(tl * 0.7 + phase) * 18) % 1120;
          n.style.transform = `translate(${(x - parseFloat(n.style.left)).toFixed(1)}px,${(y - parseFloat(n.style.top)).toFixed(1)}px)`;
        });

        const qc = smooth((tl - gap.credit) / gap.credit_dur);
        const step = Number(gap.line_step ?? 0.28);
        u.lines.forEach((n, i) => {
          const q = smooth((tl - (gap.text1 + i * step)) / gap.text_dur);
          n.style.opacity = q.toFixed(3);
          n.style.transform = `translateY(${((1 - q) * gap.rise).toFixed(1)}px)`;
        });
        for (const [n, q, dy] of [[u.credit, qc, 10], [u.source, qc, 10]]) {
          n.style.opacity = q.toFixed(3);
          n.style.transform = `translateY(${((1 - q) * dy).toFixed(1)}px)`;
        }

        u.veil.style.opacity = smooth((tl - (s.sec - trans)) / Math.max(0.01, trans)).toFixed(3);
      },
    };
  }

  async function build() {
    // 预载封面，避免第一帧闪白
    const covers = [...new Set(scenes.map((s) => s.sc.cover))].map((f) => A(f));
    await Promise.all(covers.map((src) => new Promise((res) => {
      const im = new Image();
      im.onload = im.onerror = res;
      im.src = src;
    })));

    if (cfg.bgm && cfg.bgm.src) {
      const gain = Number(cfg.bgm.gain_db ?? -13);
      music.push({
        src: P(cfg.bgm.src),
        from: Number(cfg.bgm.from ?? 0), at: 0, dur: END + TAIL,
        gain_curve: [[0, gain], [END, gain], [END + TAIL, gain - 9]],
        fade_in: Number(cfg.bgm.fade_in ?? 2.4),
        fade_out: Number(cfg.bgm.fade_out ?? 3.0),
        bgm: true,
        user_request: cfg.bgm.user_request || "用户指定的 BGM",
      });
    }

    return scenes.map((s) => makeScene(s));
  }

  return {
    COLD: 0,
    TAIL,
    meta: { title: cfg.title || "poetry", n: cfg.id || "poetry" },
    hits: [], blur: [], clips: [], music, sfx: [], sections: [],
    build,
  };
}
