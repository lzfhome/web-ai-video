// poetry 入口：从作品目录读 poem.json；画面、时间、版式全部由 poem.json 决定。
// 引擎归这条 line 所有，作品目录不再放 film.js / poetry.js。
const { createPoetryFilm } = await import(`./poetry.js?v=${Date.now()}`);

const q = new URLSearchParams(location.search);
const lesson = q.get("lesson") || "";
const base = new URL(`/lessons/${lesson}/`, location.origin);
const poem = await (await fetch(new URL("poem.json", base))).json();

export const { COLD, TAIL, meta, hits, blur, clips, music, sfx, sections, build } =
  createPoetryFilm(poem, base.href);
