// poetry 产线骨架：版式、调色板、特效、时长全部来自 poem.json。
// 换一首诗只改 poem.json，不改这个文件。
import { createPoetryFilm } from "/line/vibe-knowledge/poetry/poetry.js";

const poem = await (await fetch(new URL("./poem.json", import.meta.url))).json();

export const { COLD, TAIL, meta, hits, blur, clips, music, sfx, sections, build } =
  createPoetryFilm(poem, import.meta.url);
