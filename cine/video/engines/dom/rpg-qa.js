// RPG 对话框样片引擎：240×90 像素场景 + 深蓝对话框 + 选项菜单 + 获得物品框。
// 纯代码，无 AI 图。由各 lesson 的 film.js 传入 cfg。
import { clamp, lerp, eOutCubic, el, css, rng } from "./util.js";

const typed = (txt, t, a, cps = 22) => (t < a ? "" : txt.slice(0, Math.floor((t - a) * cps)));
const pop = (t, at, d = 0.3) => eOutCubic(clamp((t - at) / d));

const SCENES = {
  village: {
    sky: ["#24306E", "#2E3C86", "#3C4C9C", "#5464AE", "#7A78B8", "#B68CB0"],
    star: "#F4F4F4", ground: "#3D6B3A", grass: "#5A8F4E",
    building: "#7A4A32", roof: "#9A3A28", beam: "#4A2A1A", door: "#E8C88A",
    pole: "#8A5A30", villager: "#C8603A", skin: "#F0C8A0", hero: "#2A6CF0", hair: "#3A2418", moon: null,
  },
  tavern: {
    sky: ["#2A1E3E", "#3A284C", "#4A345A", "#5C4268", "#7A5276", "#B07A8A"],
    star: "#F4E4C0", ground: "#5A4A2A", grass: "#7A6A3A",
    building: "#8A5A3A", roof: "#B05A3A", beam: "#4A2A1A", door: "#F0C88A",
    pole: "#8A5A30", villager: "#C8603A", skin: "#F0C8A0", hero: "#2A6CF0", hair: "#3A2418", moon: null,
  },
  night: {
    sky: ["#0A0C1C", "#12142A", "#1A1A38", "#2A1A3A", "#3A1A2E", "#5A1A2A"],
    star: "#F4E4C0", ground: "#1A1020", grass: "#2A2030",
    building: "#2A1A2A", roof: "#6A1A28", beam: "#2A1018", door: "#D08A3A",
    pole: "#8A5A30", villager: "#8A3A3A", skin: "#F0C8A0", hero: "#E0C040", hair: "#2A1810", moon: "#D04A3A",
  },
  moon: {
    sky: ["#080C1C", "#0D1228", "#121A38", "#182044", "#20264F", "#2A2C58"],
    star: "#F4F0E8", ground: "#12101C", grass: "#1E1830",
    building: "#15101A", roof: "#2A1620", beam: "#0A0810", door: "#E0B060",
    pole: "#4A2A1A", villager: "#8A6A5A", skin: "#F0C8A0", hero: "#E0C040", hair: "#1A1010",
    moon: "#F4E8C0", moonGlow: "rgba(244,232,192,.18)",
  },
};

function pinePx(P, x, base, h, color = "#1A2438") {
  const trunk = Math.round(h * 0.32);
  P(x, base - trunk, 1, trunk, "#3A2418");
  const canopy = h - trunk;
  for (let row = 0; row < canopy; row++) {
    const w = Math.max(1, Math.round((row / Math.max(1, canopy)) * h * 0.3));
    P(x - w, base - h + row, w * 2, 1, color);
  }
  P(x, base - h, 1, 1, "#6A8A62");
}

function drawMoonPath(g, P, t, sc) {
  sc.sky.forEach((c, i) => P(0, i * 9, 240, 9, c));

  // 星星：缓慢漂移
  for (let i = 0; i < 26; i++) {
    const x = (i * 43 + Math.round(t * (3 + (i % 3) * 2))) % 240;
    const y = (i * 11) % 48;
    P(x, y, 1, 1, i % 7 === 0 ? "#FFD84A" : sc.star);
  }

  // 月亮 + 月晕
  g.fillStyle = "rgba(244,232,192,.08)";
  g.beginPath(); g.arc(204, 16, 14, 0, Math.PI * 2); g.fill();
  g.fillStyle = sc.moon;
  g.beginPath(); g.arc(204, 16, 8, 0, Math.PI * 2); g.fill();
  P(201, 13, 2, 1, "rgba(160,140,90,.28)");
  P(206, 18, 1, 1, "rgba(160,140,90,.25)");

  // 远山两层
  for (let x = 0; x < 240; x += 2) {
    const h = 5 + Math.round(6 * Math.sin(x * 0.075 + 1.2) + 3 * Math.sin(x * 0.19));
    P(x, 52 - h, 2, h, "#161C30");
  }
  for (let x = 0; x < 240; x += 2) {
    const h = 4 + Math.round(5 * Math.sin(x * 0.11 + 2.1) + 2 * Math.sin(x * 0.31));
    P(x, 61 - h, 2, h, "#101426");
  }

  P(0, 66, 240, 24, sc.ground);

  // 山路：从地平线向画面下方展开
  for (let y = 66; y < 90; y++) {
    const w = Math.round(8 + (y - 66) * 2.1);
    P(120 - Math.floor(w / 2), y, w, 1, "#3A3040");
  }
  for (let i = 0; i < 7; i++) {
    const y = 67 + i * 4;
    const w = Math.round(8 + (y - 66) * 2.1);
    P(120 + Math.round(Math.sin(t * 1.5 + i) * 3), y, 1, 2, "#8A7A62");
  }

  // 松树剪影
  pinePx(P, 38, 74, 24);
  pinePx(P, 210, 76, 26);
  pinePx(P, 24, 82, 15);
  pinePx(P, 228, 84, 13);

  // 小人和提灯：远处两个像素角色
  const bob = Math.round(Math.sin(t * 2.6) * 1);
  P(98, 66 + bob, 3, 6, "#2A6CF0");
  P(99, 64 + bob, 2, 2, "#F0C8A0");
  P(101, 68 + bob, 1, 2, "#FFD84A");
  P(139, 66 - bob, 3, 6, "#4A3A7A");
  P(140, 64 - bob, 2, 2, "#F0C8A0");
  P(138, 69 - bob, 1, 3, "#F4F4F4");

  // 萤火虫
  const fx = 80 + Math.round(Math.sin(t * 0.9) * 18);
  const fy = 48 + Math.round(Math.cos(t * 1.3) * 6);
  P(fx, fy, 1, 1, "#FFD84A");
  P(fx - 2, fy + 1, 1, 1, "rgba(255,216,74,.45)");
}

function sceneAt(cfg, t) {
  if (!cfg.scenes || !cfg.scenes.length) return { key: cfg.scene || "moon", start: 0 };
  let key = cfg.scenes[0][1];
  let start = cfg.scenes[0][0];
  for (const [at, k] of cfg.scenes) {
    if (t >= at) {
      key = k;
      start = at;
    }
  }
  return { key, start };
}

function drawFork(g, P, t, sc) {
  sc.sky.forEach((c, i) => P(0, i * 9, 240, 9, c));
  for (let i = 0; i < 22; i++) P((i * 47) % 240, (i * 13) % 46, 1, 1, i % 7 === 0 ? "#FFD84A" : sc.star);
  g.fillStyle = "rgba(244,232,192,.08)";
  g.beginPath(); g.arc(204, 16, 14, 0, Math.PI * 2); g.fill();
  g.fillStyle = sc.moon;
  g.beginPath(); g.arc(204, 16, 8, 0, Math.PI * 2); g.fill();

  for (let x = 0; x < 240; x += 2) {
    const h = 5 + Math.round(6 * Math.sin(x * 0.075 + 1.2) + 3 * Math.sin(x * 0.19));
    P(x, 52 - h, 2, h, "#161C30");
  }
  P(0, 66, 240, 24, sc.ground);

  // 岔路：左路 / 右路
  for (let y = 66; y < 90; y++) {
    const w = Math.round(5 + (y - 66) * 1.5);
    P(120 - Math.round((y - 66) * 1.4) - Math.floor(w / 2), y, w, 1, "#3A3040");
    P(120 + Math.round((y - 66) * 1.4) - Math.floor(w / 2), y, w, 1, "#3A3040");
  }
  for (let i = 0; i < 4; i++) {
    P(114 - i * 4, 69 + i * 5, 1, 2, "#8A7A62");
    P(126 + i * 4, 69 + i * 5, 1, 2, "#8A7A62");
  }

  // 两块路牌
  P(80, 48, 2, 20, "#5A3A22");
  P(70, 46, 22, 9, "#8A5A30");
  P(74, 49, 12, 1, "#C9A06A");
  P(158, 48, 2, 20, "#5A3A22");
  P(148, 46, 22, 9, "#8A5A30");
  P(152, 49, 12, 1, "#C9A06A");

  const bob = Math.round(Math.sin(t * 2.6) * 1);
  P(111, 68 + bob, 3, 6, "#2A6CF0");
  P(112, 66 + bob, 2, 2, "#F0C8A0");
  P(128, 68 - bob, 3, 6, "#4A3A7A");
  P(129, 66 - bob, 2, 2, "#F0C8A0");
}

function drawParallax(g, P, t, sc) {
  sc.sky.forEach((c, i) => P(0, i * 9, 240, 9, c));
  for (let i = 0; i < 22; i++) P((i * 43 + Math.round(t * 4)) % 240, (i * 11) % 48, 1, 1, sc.star);

  // 月亮固定，树从左往右退
  g.fillStyle = "rgba(244,232,192,.08)";
  g.beginPath(); g.arc(202, 17, 14, 0, Math.PI * 2); g.fill();
  g.fillStyle = sc.moon;
  g.beginPath(); g.arc(202, 17, 8, 0, Math.PI * 2); g.fill();

  for (let x = 0; x < 240; x += 2) {
    const h = 4 + Math.round(4 * Math.sin(x * 0.1 + 2.1));
    P(x, 58 - h, 2, h, "#101426");
  }
  P(0, 66, 240, 24, sc.ground);

  // 山路
  for (let y = 66; y < 90; y++) {
    const w = Math.round(7 + (y - 66) * 1.9);
    P(120 - Math.floor(w / 2), y, w, 1, "#3A3040");
  }
  for (let i = 0; i < 6; i++) {
    const y = 68 + i * 4;
    P(120 + Math.round(Math.sin(t * 1.8 + i) * 2), y, 1, 2, "#8A7A62");
  }

  // 远、近两层树：近层更快
  for (let i = 0; i < 4; i++) {
    const x = ((i * 82 - t * 34) % 320 + 320) % 320 - 40;
    pinePx(P, x, 72, 22, "#141C2E");
  }
  for (let i = 0; i < 4; i++) {
    const x = ((i * 76 - t * 18) % 320 + 320) % 320 - 40;
    pinePx(P, x, 84, 36, "#1A2438");
  }

  // 视线：你 -> 月亮
  for (let i = 0; i < 8; i++) {
    const k = i / 8;
    P(Math.round(120 + (202 - 120) * k), Math.round(84 + (17 - 84) * k), 1, 1, "rgba(224,176,96,.55)");
  }
  P(117, 78, 4, 7, "#2A6CF0");
  P(118, 76, 2, 2, "#F0C8A0");
  P(120, 82, 1, 2, "#FFD84A");
}

function drawDistance(g, P, t, sc) {
  sc.sky.forEach((c, i) => P(0, i * 9, 240, 9, c));
  for (let i = 0; i < 30; i++) P((i * 37 + Math.round(t * 2)) % 240, (i * 17) % 70, 1, 1, i % 9 === 0 ? "#FFD84A" : sc.star);

  // 地球
  g.fillStyle = "rgba(80,150,220,.18)";
  g.beginPath(); g.arc(30, 58, 14, 0, Math.PI * 2); g.fill();
  g.fillStyle = "#4F8FC9";
  g.beginPath(); g.arc(30, 58, 8, 0, Math.PI * 2); g.fill();
  P(27, 56, 2, 2, "#8FD0FF");

  // 月球
  g.fillStyle = "rgba(244,232,192,.10)";
  g.beginPath(); g.arc(202, 26, 24, 0, Math.PI * 2); g.fill();
  g.fillStyle = sc.moon;
  g.beginPath(); g.arc(202, 26, 15, 0, Math.PI * 2); g.fill();
  P(197, 21, 3, 2, "rgba(160,140,90,.3)");
  P(207, 30, 2, 2, "rgba(160,140,90,.25)");

  // 地月连线 + 移动光点
  for (let i = 0; i < 12; i++) {
    const k = i / 12;
    P(Math.round(30 + (202 - 30) * k), Math.round(58 + (26 - 58) * k), 1, 1, "rgba(159,179,200,.45)");
  }
  const k = (t * 0.18) % 1;
  P(Math.round(30 + (202 - 30) * k), Math.round(58 + (26 - 58) * k), 2, 2, "#FFD84A");
}

function portraitCanvas(kind) {
  const cv = document.createElement("canvas");
  cv.width = 48;
  cv.height = 48;
  cv.style.cssText = "width:100%;height:100%;display:block;image-rendering:pixelated;";
  const g = cv.getContext("2d");
  const P = (x, y, w, h, c) => { g.fillStyle = c; g.fillRect(x, y, w, h); };

  P(0, 0, 48, 48, kind === "question" ? "#1B2440" : "#1B1A2E");
  if (kind === "question") {
    P(10, 32, 28, 16, "#2A6CF0");
    P(14, 31, 20, 3, "#1A4A9A");
    P(10, 36, 4, 12, "#1A4A9A");
    P(34, 36, 4, 12, "#1A4A9A");
    P(18, 16, 12, 15, "#F0C8A0");
    P(15, 10, 18, 8, "#14141E");
    P(13, 17, 4, 10, "#14141E");
    P(31, 17, 4, 10, "#14141E");
    P(20, 23, 2, 2, "#16161E");
    P(27, 23, 2, 2, "#16161E");
    P(23, 28, 3, 1, "#A05A4A");
    P(7, 36, 7, 9, "#FFD84A");
    P(8, 37, 5, 7, "#FFF3C4");
    P(8, 34, 5, 1, "#8A5A30");
  } else {
    P(9, 32, 30, 16, "#4A3A7A");
    P(14, 31, 20, 3, "#2A1E4A");
    P(9, 36, 5, 12, "#2A1E4A");
    P(34, 36, 5, 12, "#2A1E4A");
    P(18, 15, 12, 15, "#F0C8A0");
    P(15, 9, 18, 8, "#F4F4F4");
    P(13, 16, 4, 12, "#F4F4F4");
    P(31, 16, 4, 12, "#F4F4F4");
    P(19, 22, 5, 4, "#0A0A12");
    P(25, 22, 5, 4, "#0A0A12");
    P(20, 23, 3, 2, "#8FD0FF");
    P(26, 23, 3, 2, "#8FD0FF");
    P(20, 30, 9, 4, "#F4F4F4");
    P(18, 34, 13, 9, "#F4F4F4");
    P(34, 32, 2, 16, "#6A4426");
    P(32, 29, 2, 2, "#FFD84A");
    P(35, 28, 2, 2, "#FFD84A");
    P(37, 30, 2, 2, "#FFD84A");
    P(35, 32, 2, 2, "#FFD84A");
  }
  return cv;
}

export async function buildRPGQA(ctx, cfg) {
  const END = cfg.end || ctx.narr.total;
  const videoBgs = {};
  for (const [key, spec] of Object.entries(cfg.videoBgs || {})) {
    const images = [];
    const dir = spec.dir.replace(/\/$/, "");
    for (let i = 1; i <= spec.frames; i++) {
      const im = new Image();
      im.src = `${dir}/${String(i).padStart(4, "0")}.jpg`;
      images.push(im);
    }
    await Promise.all(images.map((im) => im.decode().catch(() => {})));
    videoBgs[key] = { ...spec, images };
  }

  return [{
    from: 0,
    to: END,
    build(root) {
      const s = el(root, "shot");
      el(s, "abs", "inset:0;background:#0A0C1C;");

      const cv = document.createElement("canvas");
      cv.width = 240; cv.height = 90;
      cv.style.cssText = "position:absolute;left:0;top:0;width:1920px;height:720px;image-rendering:pixelated;";
      s.appendChild(cv);
      const g = cv.getContext("2d");
      const P = (x, y, w, h, c) => { g.fillStyle = c; g.fillRect(Math.round(x), Math.round(y), w, h); };

      const box = (x, y, w, h) => el(s, "abs", `left:${x}px;top:${y}px;width:${w}px;height:${h}px;background:#141A46;border:6px solid #F4F4F4;border-radius:0;box-shadow:6px 6px 0 rgba(5,7,14,.85),inset 0 0 0 4px #2C3680;box-sizing:border-box;`);
      const dlg = box(70, 740, 1780, 300);
      const tag = el(s, "abs cn", "left:110px;top:706px;padding:6px 24px;background:#141A46;border:5px solid #F4F4F4;border-radius:0;box-shadow:5px 5px 0 rgba(5,7,14,.85);font-size:34px;font-weight:800;color:#FFD84A;", cfg.label);
      const hasImagePortrait = Boolean(cfg.portraits && cfg.portraits.question);
      const useCodePortrait = !hasImagePortrait && cfg.codePortraits !== false;
      const showPortrait = hasImagePortrait || useCodePortrait;
      const txt = el(dlg, "abs cn", `${showPortrait ? "left:300px;" : "left:44px;"}top:34px;right:44px;font-size:56px;font-weight:700;color:#F4F4F4;line-height:1.55;letter-spacing:2px;`);
      const arrow = el(dlg, "abs", "right:40px;bottom:24px;width:0;height:0;border-left:16px solid transparent;border-right:16px solid transparent;border-top:20px solid #F4F4F4;");
      let portraitQ = null, portraitA = null;
      const frameStyle = "left:40px;top:40px;width:210px;height:210px;border:6px solid #F4F4F4;background:#0A0C1C;box-sizing:border-box;overflow:hidden;image-rendering:pixelated;box-shadow:5px 5px 0 rgba(5,7,14,.85);";
      if (hasImagePortrait) {
        const frameQ = el(dlg, "abs", frameStyle);
        portraitQ = el(frameQ, "abs", "inset:0;background-position:center;background-size:cover;image-rendering:pixelated;");
        portraitQ.style.backgroundImage = `url("${cfg.portraits.question}")`;
        const frameA = el(dlg, "abs", `${frameStyle}opacity:0;`);
        portraitA = el(frameA, "abs", "inset:0;background-position:center;background-size:cover;image-rendering:pixelated;");
        portraitA.style.backgroundImage = `url("${cfg.portraits.answer}")`;
      } else if (useCodePortrait) {
        const frameQ = el(dlg, "abs", frameStyle);
        portraitQ = portraitCanvas("question");
        frameQ.appendChild(portraitQ);
        const frameA = el(dlg, "abs", `${frameStyle}opacity:0;`);
        portraitA = portraitCanvas("answer");
        frameA.appendChild(portraitA);
      }

      const menu = box(1240, 350, 610, 320);
      const items = cfg.options.map((w, i) => el(menu, "abs cn", `left:80px;top:${50 + i * 100}px;font-size:46px;font-weight:800;color:#F4F4F4;`, w));
      const cur = el(menu, "abs", "left:32px;width:0;height:0;border-top:18px solid transparent;border-bottom:18px solid transparent;border-left:26px solid #FFD84A;");
      const get = el(s, "abs cn", "left:610px;top:250px;width:700px;padding:26px 0;text-align:center;background:#141A46;border:6px solid #FFD84A;border-radius:0;font-size:72px;font-weight:900;color:#FFD84A;box-shadow:6px 6px 0 rgba(5,7,14,.85);", cfg.reward);

      return { s, cv, g, P, dlg, tag, txt, arrow, menu, items, cur, get, portraitQ, portraitA };
    },
    render(t, u) {
      const { g, P } = u;
      const F = t >= cfg.finalAt;
      const R = rng(4);
      const scene = sceneAt(cfg, t);
      const sceneKey = scene.key;
      const sc = SCENES[sceneKey] || SCENES.moon;
      const bg = videoBgs[sceneKey];
      const bgIndex = bg ? Math.floor((t - scene.start) * bg.fps) % bg.frames : -1;
      const bgImage = bg && bgIndex >= 0 ? bg.images[bgIndex] : null;
      css(u.s, {
        transform: `translate(${(Math.sin(t * 0.7) * 4).toFixed(1)}px,${(Math.cos(t * 0.5) * 2).toFixed(1)}px)`,
      });

      g.clearRect(0, 0, 240, 90);

      if (bgImage && bgImage.complete && bgImage.naturalWidth) {
        g.drawImage(bgImage, 0, 0, 240, 90);
      } else if (sceneKey === "moonPath") {
        drawMoonPath(g, P, t, sc);
      } else if (sceneKey === "fork") {
        drawFork(g, P, t, sc);
      } else if (sceneKey === "parallax") {
        drawParallax(g, P, t, sc);
      } else if (sceneKey === "distance") {
        drawDistance(g, P, t, sc);
      } else {
        sc.sky.forEach((c, i) => P(0, i * 9, 240, 9, c));
        for (let i = 0; i < 14; i++) P((i * 37) % 240, (i * 11) % 36, 1, 1, sc.star);
        if (sc.moon) {
          g.beginPath(); g.arc(205, 18, 8, 0, Math.PI * 2); g.fillStyle = sc.moon; g.fill();
          g.beginPath(); g.arc(205, 18, 13, 0, Math.PI * 2); g.fillStyle = sc.moonGlow || "rgba(208,74,58,.15)"; g.fill();
        }
        P(0, 66, 240, 24, sc.ground);
        for (let x = 0; x < 240; x += 8) P(x, 66, 4, 2, sc.grass);
        P(40, 34, 100, 32, sc.building);
        P(40, 34, 100, 3, sc.beam);
        P(70, 22, 40, 12, sc.roof);
        P(64, 20, 52, 3, sc.beam);
        P(82, 48, 16, 18, sc.door);

        const lx = F && t > cfg.moveAt ? lerp(160, 200, clamp((t - cfg.moveAt) / 1.2)) : 160;
        if (F && t > cfg.moveAt) P(lx - 12, 50, 26, 3, sc.pole); else P(160, 30, 3, 36, sc.pole);

        for (let i = 0; i < 6; i++) {
          const x = 120 + i * 14 + Math.floor(R() * 4);
          P(x, 58, 6, 8, sc.villager);
          P(x + 1, 54, 4, 4, sc.skin);
        }

        const hx = F ? (t < cfg.moveAt ? lerp(212, 162, clamp((t - cfg.finalAt) / 0.6)) : lx - 2) : 212;
        P(hx, 56, 6, 10, sc.hero);
        P(hx + 1, 51, 4, 5, sc.skin);
        P(hx, 50, 6, 2, sc.hair);
      }

      // 像素萤火虫：让长对话镜头保持一点点运动
      const fx = Math.floor((t * 12) % 240);
      const fy = 18 + Math.round(Math.sin(t * 2.2) * 8);
      P(fx, fy, 3, 3, "#FFD84A");
      P(fx - 3, fy + 3, 1, 1, "rgba(255,216,74,.55)");
      P(fx + 4, fy - 2, 1, 1, "rgba(255,216,74,.4)");

      const L = [...cfg.lines].reverse().find(([a]) => t >= a);
      u.txt.textContent = L ? typed(L[1], t, L[0], 22) : "";
      css(u.arrow, { opacity: String(L && t - L[0] > L[1].length / 22 && Math.floor(t * 3) % 2 ? 1 : 0) });

      css(u.tag, { opacity: String(t >= 0.1 ? 1 : 0) });
      u.tag.textContent = t >= cfg.finalAt
        ? (cfg.answerLabel || cfg.tag2)
        : t >= cfg.menuAt ? cfg.tag2 : cfg.label;
      if (u.portraitQ) {
        const showAnswer = t >= cfg.finalAt;
        const bob = Math.sin(t * 2.8) * 3;
        css(u.portraitQ.parentElement, { opacity: showAnswer ? "0" : "1", transform: `translateY(${bob.toFixed(1)}px)` });
        css(u.portraitA.parentElement, { opacity: showAnswer ? "1" : "0", transform: `translateY(${(-bob).toFixed(1)}px)` });
      }

      css(u.menu, { opacity: String(t >= cfg.menuAt && t < cfg.rewardAt + 0.4 ? 1 : 0) });
      const sel = F ? cfg.final : cfg.cursor;
      css(u.cur, { top: `${62 + sel * 100}px`, opacity: String(F && Math.floor(t * 6) % 2 ? 0.3 : 1) });
      u.items.forEach((n, i) => css(n, { color: i === sel ? "#FFD84A" : "#F4F4F4" }));

      const pg = pop(t, cfg.rewardAt, 0.3);
      const ph = 1 - clamp((t - (cfg.rewardAt + 2.4)) / 0.4);
      css(u.get, { opacity: String(pg * ph > 0 ? 1 : 0), transform: `scale(${pg.toFixed(3)})` });
    },
  }];
}
