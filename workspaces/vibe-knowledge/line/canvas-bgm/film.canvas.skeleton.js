// Canvas 快速通道模板（BGM-only）
// 组件 API 见 cine/video/engines/canvas/components.js
import {bg, title, foot, chapter, progress} from "../../cine/canvas/components.js";

export const duration = 10;
export const fps = 30;
export const images = [];

export async function build(c) {
  return [
    {
      from: 0,
      to: duration,
      draw(t) {
        bg(c);
        title(c, {text: "__TITLE__", sub: "Canvas 快速通道", u: Math.min(1, t / 0.6)});
        foot(c, {text: "BGM-only · Canvas / WebCodecs"});
        chapter(c, {index: 1, total: 1});
        progress(c, {t, duration});
      },
    },
  ];
}
