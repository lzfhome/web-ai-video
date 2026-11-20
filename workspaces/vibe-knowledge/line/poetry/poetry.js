// poetry 引擎：书封决定画面 + 代码排版诗句 + BGM。
//
// 背景、书封、雾、光斑、浮尘全部是 DOM/CSS；文字用系统字体渲染，始终锐利。
// 参数全部来自 lessons/<id>/poem.json：
//   const poem = await (await fetch(new URL("./poem.json", import.meta.url))).json();
//   export const {...} = createPoetryFilm(poem, import.meta.url);
import { clamp, el } from "/cine/engine/util.js";

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
  const TAIL = Number(cfg.tail ?? 0.3);
  const GLOBAL_GAP = { ...GAP, ...(cfg.gap || {}) };
  const GLOBAL_FX = { ...FX, ...(cfg.effects || {}) };
  // credit_size 留空就按字号比例跟随主句，避免小字场景里署名反而比正文大
  const TYPE = { size: 70, credit_size: 0, credit_ratio: 0.6, source_size: 19, tracking: 4, footer_size: 18, ...(cfg.type || {}) };
  // 时长按字数算：lead + 字数×char + 署名停留 + 收尾
  const TIMING = { lead: 1.2, char: 0.1, credit_hold: 2.4, tail: 0.8, after: 0, min: 4, max: 14, ...(cfg.timing || {}) };
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

  // 把一场的文字拼成实际渲染的行（含台词引号）
  const sceneBodies = (sc) => {
    const lines = (sc.lines && sc.lines.length ? sc.lines : [sc.line1, sc.line2]).filter(Boolean);
    const quoted = !!sc.quotes;
    return lines.map((txt, i) => {
      let body = txt;
      if (quoted && i === 0) body = "「" + body;
      if (quoted && i === lines.length - 1) body = body + "」";
      return body;
    });
  };

  // 每个字的出现时刻：有 pacing 就按情绪脚本，没有就匀速
  const sceneSchedule = (sc, bodies) => {
    const base = Number(TIMING.char);
    const flat = bodies.join("");
    const pace = Array.isArray(sc.pacing) ? sc.pacing : null;
    if (pace) {
      const offsets = [];
      let idx = 0, t = 0, prev = 0, ok = true;
      for (const seg of pace) {
        const text = String(seg.text ?? "");
        if (!text || flat.slice(idx, idx + text.length) !== text) { ok = false; break; }
        const c = Number(seg.char ?? base);
        for (let k = 0; k < text.length; k++) {
          if (seg.attach) {
            offsets.push(prev);
          } else {
            offsets.push(t);
            prev = t;
            t += c;
          }
        }
        t += Number(seg.pause ?? 0);
        idx += text.length;
      }
      if (ok && idx === flat.length) return { offsets, textDur: t, lastAt: offsets.length ? offsets[offsets.length - 1] : 0 };
    }
    const offsets = [];
    let t = 0;
    for (let k = 0; k < flat.length; k++) { offsets.push(t); t += base; }
    return { offsets, textDur: t, lastAt: offsets.length ? offsets[offsets.length - 1] : 0 };
  };

  let cursor = 0;
  for (const s of scenes) {
    if (s.sc.cards && s.sc.cards.length) {
      const lead = Number(s.sc.card_lead ?? 1.2);
      const tail = Number(s.sc.card_tail ?? 0.8);
      s.sec = Number(s.sc.seconds ?? (lead + s.sc.cards.reduce((a, c) => a + Number(c.seconds || 0), 0) + tail));
    } else if (s.sc.seconds != null) {
      s.sec = Number(s.sc.seconds);
    } else {
      const bodies = sceneBodies(s.sc);
      const sch = sceneSchedule(s.sc, bodies);
      s.chars = bodies.join("").length;
      s.textDur = sch.textDur;
      const lead = Number(((s.sc.gap && s.sc.gap.text1) ?? (cfg.gap && cfg.gap.text1) ?? TIMING.lead));
      const a = TIMING.after;
      if (a && typeof a === "object") {
        // 新规则：署名和章节出现后按句长停留；最后一场固定停 15 秒
        const isLast = s === scenes[scenes.length - 1];
        const hold = isLast ? 15.0 : clamp(s.textDur * Number(a.per_sec ?? 0.25), Number(a.min ?? 0.5), Number(a.max ?? 4));
        const creditFade = Number((cfg.gap && cfg.gap.credit_dur) ?? 0.95);
        s.sec = clamp(lead + sch.lastAt + 2.0 + creditFade + hold, TIMING.min, TIMING.max);
      } else {
        s.sec = clamp(
          lead + s.textDur + TIMING.credit_hold + TIMING.tail + Number(a || 0),
          TIMING.min, TIMING.max,
        );
      }
    }
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
        // 黑色卡纸/相框：在书封外再铺一层，带一点斜面高光，黑底上也能看出轮廓
        const frame = Number(book.border ?? 0);
        const mat = Number(book.mat ?? 0);
        const matColor = book.mat_color || "#f0e8d6";
        const rim = Number(book.rim ?? 0);
        const rimColor = book.rim_color || "rgba(255,248,235,.38)";
        if (frame) {
          const frameFill = book.frame_fill ||
            "linear-gradient(145deg,#242424 0%,#0a0a0a 30%,#000 52%,#0a0a0a 74%,#2b2b2b 100%)";
          el(bookWrap, "abs", `inset:${-(mat + frame)}px;background:${frameFill};` +
            `box-shadow:${rim ? `0 0 0 ${rim}px ${rimColor},` : ""}` +
            "0 40px 100px rgba(0,0,0,.86),0 10px 30px rgba(0,0,0,.62)," +
            "inset 0 1px 0 rgba(255,255,255,.10),inset 0 -1px 0 rgba(255,255,255,.06);");
        }
        if (mat) {
          el(bookWrap, "abs", `inset:${-mat}px;background:${matColor};box-shadow:inset 0 0 0 1px rgba(0,0,0,.22);`);
        }
        const bookEl = el(bookWrap, "abs", "inset:0;background-position:center;background-size:cover;");
        bookEl.style.boxShadow = "inset 0 0 0 1px rgba(255,255,255,.06),inset 0 0 26px rgba(0,0,0,.35)";
        bookEl.style.backgroundImage = `url("${cover}")`;
        el(bookWrap, "abs", "left:0;top:0;width:16px;height:100%;background:linear-gradient(90deg,rgba(0,0,0,.42),rgba(0,0,0,0));");
        el(bookWrap, "abs", `left:-14px;top:-12px;width:116px;height:26px;background:${pal.tab};transform:rotate(-5deg);box-shadow:0 3px 10px rgba(0,0,0,.2);opacity:.85;`);
        const sweep = el(bookEl, "abs", `left:-60%;top:-20%;width:55%;height:140%;background:linear-gradient(90deg,transparent,rgba(255,255,255,.20),transparent);transform:rotate(14deg);mix-blend-mode:screen;opacity:${(0.18 * fx.sweep).toFixed(3)};`);

        // 角标
        el(stage, "abs mono", "left:96px;top:78px;font-size:17px;letter-spacing:7px;color:rgba(244,240,232,.52);", HEADER_LEFT);
        el(stage, "abs mono", `right:96px;top:80px;font-size:15px;letter-spacing:4px;color:${pal.headerColor};`, sc.header || "");
        const f1 = Number(TYPE.footer_size ?? 18);
        const f2 = Number(TYPE.footer2_size ?? Math.max(12, f1 - 3));
        const f3 = Number(TYPE.footer3_size ?? Math.max(11, f2 - 2));
        const foot = document.createElement("div");
        foot.style.cssText = "position:absolute;left:96px;bottom:44px;width:1620px;display:flex;flex-direction:column;gap:5px;align-items:flex-start;";
        stage.appendChild(foot);
        const addFoot = (text, size, track, alpha) => {
          if (!text) return;
          const d = document.createElement("div");
          d.className = "mono";
          d.style.cssText = `font-size:${size}px;letter-spacing:${track}px;line-height:1.45;color:rgba(244,240,232,${alpha});white-space:normal;`;
          d.textContent = text;
          foot.appendChild(d);
        };
        addFoot(sc.footer, f1, 2.5, 0.56);
        addFoot(sc.footer2, f2, 2, 0.38);
        addFoot(sc.footer3, f3, 2, 0.3);
        let bioSlot = null;
        if (sc.cards && sc.cards.length > 1) {
          bioSlot = document.createElement("div");
          bioSlot.className = "mono";
          bioSlot.style.cssText = `font-size:${f3}px;letter-spacing:2px;line-height:1.45;color:rgba(244,240,232,0.3);white-space:normal;`;
          bioSlot.textContent = sc.footer4 || "";
          foot.appendChild(bioSlot);
        } else {
          addFoot(sc.footer4, f3, 2, 0.3);
        }

        const grain = el(stage, "abs", `inset:0;background-image:url("/resources/images/noise.png");background-size:512px 512px;opacity:${Number(fx.grain).toFixed(3)};mix-blend-mode:overlay;pointer-events:none;`);
        el(stage, "abs", `inset:0;background:radial-gradient(ellipse at 50% 46%,transparent 36%,rgba(0,0,0,${clamp(fx.vignette, 0, 1)}) 100%);pointer-events:none;`);

        const families = FONT.replace(/^\s*font-family\s*:/, "").replace(/;\s*$/, "");
        const mctx = document.createElement("canvas").getContext("2d");

        // 单句和多卡共用：量宽、定字号、行高、文字 CSS
        const layoutText = (src) => {
          const lines = (src.lines && src.lines.length ? src.lines : [src.line1, src.line2]).filter(Boolean);
          const bodies = sceneBodies(src);
          const tSize0 = Number((src.type && src.type.size) ?? TYPE.size);
          const tTrack = Number((src.type && src.type.tracking) ?? TYPE.tracking);
          mctx.font = `${tSize0}px ${families}`;
          let needW = 0;
          for (const body of bodies) {
            needW = Math.max(needW, mctx.measureText(body).width + tTrack * Math.max(0, body.length - 1));
          }
          const slack = src.quotes ? 0.25 * tSize0 : 0;
          const tSize = needW - slack > 1052 ? tSize0 * (1052 / (needW - slack)) : tSize0;
          const cSize = Number((src.type && src.type.credit_size) ?? (TYPE.credit_size || Math.round(tSize * TYPE.credit_ratio)));
          const sSize = Number((src.type && src.type.source_size) ?? TYPE.source_size);
          const lineH = tSize * 1.9;
          const top = 470 - ((lines.length - 1) * lineH) / 2;
          const textCss = `left:760px;width:1080px;${FONT}font-size:${tSize}px;line-height:1.9;letter-spacing:${tTrack}px;color:${pal.text};text-shadow:0 3px 28px rgba(0,0,0,.8),0 0 20px rgba(255,236,200,${(0.12 * fx.text_glow).toFixed(3)});`;
          return { lines, bodies, tSize, cSize, sSize, lineH, top, textCss };
        };

        // 多卡场景：封面/背景不动，只换文字块和小传
        if (sc.cards && sc.cards.length > 1) {
          const cardNodes = [];
          const lead = Number(sc.card_lead ?? 1.2);
          let at = lead;
          for (const card of sc.cards) {
            const { bodies, lines, cSize, sSize, lineH, top, textCss } = layoutText(card);
            const node = el(shot, "abs", "inset:0;opacity:0;");
            bodies.forEach((body, k) => {
              const line = document.createElement("div");
              line.className = "abs";
              line.style.cssText = `top:${(top + k * lineH).toFixed(0)}px;${textCss}`;
              line.textContent = body;
              node.appendChild(line);
            });
            const creditTop = top + lines.length * lineH + 38;
            const hasCredit = !card.narration && !!card.credit;
            if (hasCredit) {
              const c = document.createElement("div");
              c.className = "abs";
              c.style.cssText = `left:764px;top:${creditTop.toFixed(0)}px;${FONT}font-size:${cSize}px;letter-spacing:3px;color:${pal.credit};`;
              c.textContent = card.quotes ? `——${card.credit}` : card.credit;
              node.appendChild(c);
            }
            const sourceTop = hasCredit ? creditTop + cSize * 1.55 : creditTop;
            const src = document.createElement("div");
            src.className = "abs";
            src.style.cssText = `left:766px;top:${sourceTop.toFixed(0)}px;${FONT}font-size:${sSize}px;letter-spacing:2px;color:${pal.sourceColor};`;
            src.textContent = card.source || "";
            node.appendChild(src);

            const sec = Number(card.seconds || 0);
            cardNodes.push({ node, start: at, end: at + sec, bio: card.footer4 || "" });
            at += sec;
          }
          const veil = el(shot, "abs", "inset:0;background:#04060A;opacity:0;pointer-events:none;");
          return {
            s: shot, stage, bg, mist1, mist2, mist3, bokeh, dust, bookWrap, halo, sweep, grain, veil,
            cardData: { nodes: cardNodes, bioSlot, idx: -1 },
          };
        }

        // 诗句：逐字出现（打字机），每个字一个 span
        const { bodies, lines, cSize, sSize, lineH, top, textCss } = layoutText(sc);
        // 旁白：不加引号、不署名，靠字形和台词区分
        const isNarr = !!sc.narration;
        const charNodes = [];
        bodies.forEach((body, i) => {
          const node = el(shot, "abs", `top:${(top + i * lineH).toFixed(0)}px;${textCss}`);
          for (const ch of Array.from(body)) {
            const span = document.createElement("span");
            span.textContent = ch;
            span.style.opacity = "0";
            span.style.whiteSpace = "pre";
            if (ch === "「") span.style.marginRight = "-0.25em";
            if (ch === "」") span.style.marginLeft = "-0.25em";
            node.appendChild(span);
            charNodes.push(span);
          }
        });
        const charDur = Number(TIMING.char);
        const sch = sceneSchedule(sc, bodies);
        const textStart = Number(gap.text1 ?? TIMING.lead);
        const creditAt = textStart + (sch.lastAt ?? sch.textDur) + 2.0;
        const creditTop = top + lines.length * lineH + 38;
        const hasCredit = !isNarr && !!sc.credit;
        const creditText = sc.quotes ? `——${sc.credit}` : sc.credit;
        const credit = hasCredit
          ? el(shot, "abs", `left:764px;top:${creditTop.toFixed(0)}px;${FONT}font-size:${cSize}px;letter-spacing:3px;color:${pal.credit};opacity:0;`, creditText)
          : null;
        const sourceTop = hasCredit ? creditTop + cSize * 1.55 : creditTop;
        const source = el(shot, "abs", `left:766px;top:${sourceTop.toFixed(0)}px;${FONT}font-size:${sSize}px;letter-spacing:2px;color:${pal.sourceColor};opacity:0;`, sc.source || "");

        const veil = el(shot, "abs", "inset:0;background:#04060A;opacity:0;pointer-events:none;");

        return { s: shot, stage, bg, mist1, mist2, mist3, bokeh, dust, bookWrap, halo, sweep, grain, chars: charNodes, charOffsets: sch.offsets, charDur, textStart, creditAt, credit, source, veil };
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

        if (u.cardData) {
          const cd = u.cardData;
          const cardFade = Number(sc.card_fade ?? 1.0);
          let active = -1;
          cd.nodes.forEach((n, i) => {
            const local = tl - n.start;
            const dur = n.end - n.start;
            let op = 0;
            if (local >= 0 && local < dur) {
              active = i;
              if (local < cardFade) op = smooth(local / cardFade);
              else if (local > dur - cardFade) op = 1 - smooth((local - (dur - cardFade)) / cardFade);
              else op = 1;
            }
            n.node.style.opacity = op.toFixed(3);
          });
          if (active >= 0 && active !== cd.idx) {
            cd.idx = active;
            if (cd.bioSlot) cd.bioSlot.textContent = cd.nodes[active].bio;
          }
          u.veil.style.opacity = smooth((tl - (s.sec - trans)) / Math.max(0.01, trans)).toFixed(3);
          return;
        }

        const qc = smooth((tl - u.creditAt) / gap.credit_dur);
        const fade = Number(s.sc.fade ?? TIMING.fade ?? Math.min(0.2, u.charDur));
        u.chars.forEach((n, i) => {
          const at = u.charOffsets ? u.charOffsets[i] : i * u.charDur;
          const q = smooth((tl - (u.textStart + at)) / fade);
          n.style.opacity = q.toFixed(3);
        });
        for (const [n, q, dy] of [[u.credit, qc, 10], [u.source, qc, 10]]) {
          if (!n) continue;
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
      im.decoding = "sync";
      im.onload = () => {
        if (im.decode) im.decode().then(res, res);
        else res();
      };
      im.onerror = res;
      im.src = src;
      im.style.cssText = "position:fixed;left:-9999px;top:-9999px;width:1px;height:1px;opacity:0.01;pointer-events:none;";
      document.body.appendChild(im);
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
