(() => {
  const $ = (id) => document.getElementById(id);
  const gallery = $("gallery");
  let pollTimer = null;
  let CFG = null;
  let savedPrefs = { resolution: null, task_type: null };

  /* ---------- 素材/提示词持久化（刷新不丢） ---------- */
  const MEDIA_KEY = "vs_media_items";
  const PROMPT_KEY = "vs_pending_prompt";

  function saveMediaState() {
    try {
      localStorage.setItem(MEDIA_KEY, JSON.stringify(mediaItems));
      const p = document.getElementById("prompt");
      if (p) localStorage.setItem(PROMPT_KEY, p.value);
    } catch (err) { /* 忽略 */ }
  }

  function loadMediaState() {
    try {
      const raw = localStorage.getItem(MEDIA_KEY);
      if (raw) {
        const arr = JSON.parse(raw);
        if (Array.isArray(arr)) mediaItems = arr;
      }
      const pp = localStorage.getItem(PROMPT_KEY);
      const p = document.getElementById("prompt");
      if (pp != null && p) p.value = pp;
    } catch (err) { /* 忽略 */ }
  }
  let mediaItems = [];       // {id, kind, role, url, name}
  function multiImage() { return mediaItems.filter((it) => it.kind === "image").length > 1; }
  let ratioLocked = false;
  let durationLocked = false;

  const TASK_TYPE_LABELS = {
    auto: "auto · 自动判断",
    text: "文生视频",
    image: "图生视频",
    edit: "视频编辑（需参考视频）",
    extend: "视频延长（需参考视频）",
  };
  const ROLE_LABELS = {
    first_frame: "首帧",
    last_frame: "尾帧",
    reference_image: "参考图",
  };
  const KIND_LABELS = { image: "图片", audio: "音频", video: "参考视频" };

  /* ================= 配置 / 模型能力 ================= */

  async function loadConfig() {
    try {
      const resp = await fetch("/api/config");
      CFG = await resp.json();
      if (!CFG.configured) $("config-banner").hidden = false;

      const modelSel = $("model");
      modelSel.innerHTML = "";
      const g1 = document.createElement("optgroup");
      g1.label = "视频生成（Seedance）";
      for (const [id, label] of Object.entries(CFG.models || {})) {
        const opt = document.createElement("option");
        opt.value = id; opt.textContent = label;
        opt.selected = id === CFG.default_model;
        g1.appendChild(opt);
      }
      modelSel.appendChild(g1);
      const g2 = document.createElement("optgroup");
      g2.label = "图片生成（Seedream）";
      for (const [id, label] of Object.entries(CFG.image_models || {})) {
        const opt = document.createElement("option");
        opt.value = id; opt.textContent = label;
        g2.appendChild(opt);
      }
      modelSel.appendChild(g2);

      $("resolution").value = CFG.defaults.resolution;
      $("ratio").value = CFG.defaults.ratio;
      $("duration").value = CFG.defaults.duration;
      $("camera-fixed").checked = CFG.defaults.camera_fixed;
      $("watermark").checked = CFG.defaults.watermark;
      $("generate-audio").checked = CFG.defaults.generate_audio;
      if (CFG.defaults.seed != null) $("seed").value = CFG.defaults.seed;

      modelSel.addEventListener("change", applyModelCaps);
      loadSettings();
      loadMediaState();
      applyModelCaps();
      // 恢复设置后同步联动状态
      updateMultiUI();
      renderMediaList();
      if (typeof updateExtTunnelHint === "function") updateExtTunnelHint();
    } catch (err) { /* 由 conn 状态提示 */ }
  }

  /* ---------- 设置持久化（刷新不丢） ---------- */
  const SETTINGS_KEY = "vs_settings";

  function saveSettings() {
    try {
      const s = {
        model: $("model").value,
        task_type: $("task-type").value,
        resolution: $("resolution").value,
        ratio: $("ratio").value,
        duration: $("duration").value,
        seed: $("seed").value,
        camera_fixed: $("camera-fixed").checked,
        watermark: $("watermark").checked,
        generate_audio: $("generate-audio").checked,
        chain: $("chain-toggle").checked,
        img_size: $("img-size").value,
        img_n: $("img-n").value,
        img_seq: $("img-seq").checked,
        img_watermark: $("img-watermark").checked,
      };
      localStorage.setItem(SETTINGS_KEY, JSON.stringify(s));
    } catch (err) { /* 忽略 */ }
  }

  function loadSettings() {
    try {
      const raw = localStorage.getItem(SETTINGS_KEY);
      if (!raw) return;
      const s = JSON.parse(raw);
      savedPrefs.resolution = s.resolution || null;
      savedPrefs.task_type = s.task_type || null;
      if (s.model && [...$("model").options].some((o) => o.value === s.model)) $("model").value = s.model;
      if (s.task_type && [...$("task-type").options].some((o) => o.value === s.task_type)) $("task-type").value = s.task_type;
      if (s.resolution) $("resolution").value = s.resolution;
      if (s.ratio) $("ratio").value = s.ratio;
      if (s.duration != null) $("duration").value = s.duration;
      if (s.seed != null) $("seed").value = s.seed;
      $("camera-fixed").checked = !!s.camera_fixed;
      $("watermark").checked = !!s.watermark;
      $("generate-audio").checked = s.generate_audio !== false;
      $("chain-toggle").checked = s.chain !== false;
      if (s.img_size) $("img-size").value = s.img_size;
      if (s.img_n) $("img-n").value = s.img_n;
      $("img-seq").checked = !!s.img_seq;
      $("img-watermark").checked = !!s.img_watermark;
    } catch (err) { /* 忽略 */ }
  }

  (function bindSettingsSave() {
    const ids = ["model", "task-type", "resolution", "ratio", "duration", "seed",
      "camera-fixed", "watermark", "generate-audio", "chain-toggle",
      "img-size", "img-n", "img-seq", "img-watermark"];
    ids.forEach((id) => {
      const el = document.getElementById(id);
      if (!el) return;
      el.addEventListener("change", saveSettings);
      el.addEventListener("input", saveSettings);
    });
  })();

  function isImageModel(id) {
    return !!(CFG && CFG.image_models && CFG.image_models[id]);
  }

  function capsFor(model) {
    return (CFG && CFG.model_caps && CFG.model_caps[model]) || {
      resolutions: ["480p", "720p", "1080p"], max_duration: 15,
      inputs: ["text", "image", "video", "audio"], task_types: ["auto", "text", "image", "edit", "extend"],
      max_media: 20,
    };
  }

  function applyModelCaps() {
    if (!CFG) return;
    const model = $("model").value;
    const imgMode = isImageModel(model);

    // 图片模式：显示图片设置，隐藏视频相关
    $("video-params").style.display = imgMode ? "none" : "";
    $("image-settings").style.display = imgMode ? "" : "none";
    $("task-type-field").style.display = imgMode ? "none" : "";
    $("media-section").style.display = imgMode ? "none" : "";
    const note = $("model-note");
    if (imgMode) {
      note.textContent = "图片生成模型：文生图 / 图生图 / 组图。让 AI 写好图片提示词 → 点「✓ 应用」→ 点「✦ 生成」；生成的图会加入素材，可切回视频模式动画化。";
      note.hidden = false;
      $("extend-tags").hidden = true;
      $("extend-tips").hidden = true;
      $("extend-mode").hidden = true;
      const pro = model === "doubao-seedream-5-0-pro-260628";
      $("img-seq-wrap").style.display = pro ? "none" : "";
      toggleStoryPills(false);
      return;
    }

    const caps = capsFor(model);

    // 分辨率（优先用恢复的设置）
    const resSel = $("resolution");
    const curRes = savedPrefs.resolution || resSel.value || CFG.defaults.resolution;
    resSel.innerHTML = "";
    for (const r of caps.resolutions) {
      const opt = document.createElement("option");
      opt.value = r; opt.textContent = r;
      opt.selected = r === curRes || (r === CFG.defaults.resolution && !caps.resolutions.includes(curRes));
      resSel.appendChild(opt);
    }
    savedPrefs.resolution = null;

    // 任务类型
    const ttSel = $("task-type");
    const curTt = savedPrefs.task_type || ttSel.value || (CFG.defaults.task_type || "auto");
    ttSel.innerHTML = "";
    for (const t of caps.task_types) {
      const opt = document.createElement("option");
      opt.value = t;
      opt.textContent = TASK_TYPE_LABELS[t] || t;
      opt.selected = t === curTt || t === (CFG.defaults.task_type || "auto");
      ttSel.appendChild(opt);
    }
    savedPrefs.task_type = null;

    // 时长上限
    const dur = $("duration");
    dur.max = caps.max_duration;
    if (parseInt(dur.value) > caps.max_duration) dur.value = caps.max_duration;

    // 素材按钮可见性
    const inputs = caps.inputs || [];
    for (const kind of ["image", "audio", "video"]) {
      $("add-" + kind).style.display = inputs.includes(kind) ? "" : "none";
    }
    // 清理当前模型不支持的素材类型
    mediaItems = mediaItems.filter((it) => inputs.includes(it.kind));
    renderMediaList();

    // 模型能力总览（始终显示）
    const feats = (caps.features || []).join(" · ");
    note.textContent = "能力：" + feats;
    note.hidden = false;

    // 编辑/延长能力标签 + 提示卡：仅 2.0/2.5 等支持时显示
    const supportsExtend = (caps.task_types || []).includes("edit") || (caps.task_types || []).includes("extend");
    $("extend-tags").hidden = !supportsExtend;
    $("extend-tips").hidden = !supportsExtend;
    $("extend-mode").hidden = !supportsExtend;

    // 画面运动：mini/fast 不支持则隐藏
    const cfWrap = $("camera-fixed-wrap");
    if (cfWrap) cfWrap.style.display = caps.camera_fixed === false ? "none" : "";

    toggleStoryPills(true);
    adaptParams();
  }

  function toggleStoryPills(show) {
    // 图片模式隐藏多图相关控件
    const ct = document.getElementById("chain-toggle-wrap");
    if (ct) ct.hidden = !(show && multiImage());
    const lp = document.getElementById("load-story-prompts");
    if (lp) lp.hidden = !(show && multiImage());
    const lsp = document.getElementById("load-single-prompts");
    if (lsp) lsp.hidden = !show || multiImage();
    const as = document.getElementById("apply-storyboard");
    if (as) as.style.display = show ? "" : "none";
    const mh = document.getElementById("multi-hint");
    if (mh) mh.hidden = !(show && multiImage());
  }

  /* ================= 素材构建 ================= */

  function renderMediaList() {
    saveMediaState();
    if (typeof updateMultiUI === "function") updateMultiUI();
    const list = $("media-list");
    list.innerHTML = "";
    $("media-count").textContent = mediaItems.length ? `(${mediaItems.length})` : "";
    const caps = capsFor($("model").value);

    if (!mediaItems.length) {
      const empty = document.createElement("div");
      empty.className = "media-empty";
      empty.textContent = "暂无素材，点击下方按钮添加（可选）";
      list.appendChild(empty);
      $("media-note").hidden = true;
      return;
    }

    let over = !multiImage() && mediaItems.length > caps.max_media;
    const hasLocalVideo = mediaItems.some((it) => it.kind === "video" && it.local);
    const notes = [];
    if (over) notes.push(`该模型最多支持 ${caps.max_media} 个素材，当前 ${mediaItems.length} 个。`);
    if (multiImage()) notes.push("多图模式：每张图独立生成一段视频，可选尾帧衔接。");
    if (!multiImage() && (caps.roles || ["first_frame", "last_frame", "reference_image"]).length < 3) {
      notes.push("当前模型仅支持「首帧」图生视频；如需 尾帧/参考图，请切换到 Seedance 2.0/2.5。");
    }
    if (hasLocalVideo) notes.push("本地上传视频通过 public_base_url 公网地址供方舟访问，生成期间请保持隧道开启。");
    if (notes.length) {
      $("media-note").textContent = notes.join(" ");
      $("media-note").hidden = false;
    } else {
      $("media-note").hidden = true;
    }

    mediaItems.forEach((it, idx) => {
      const row = document.createElement("div");
      row.className = "media-item";

      const thumb = document.createElement("div");
      thumb.className = "media-thumb";
      if (it.kind === "image" && it.url.startsWith("data:")) {
        const img = document.createElement("img");
        img.src = it.url;
        thumb.appendChild(img);
      } else if (it.kind === "image") {
        const img = document.createElement("img");
        img.src = it.url;
        img.onerror = () => (thumb.textContent = "🖼");
        thumb.appendChild(img);
      } else if (it.kind === "video") {
        thumb.textContent = "🎬";
      } else {
        thumb.textContent = "🎵";
      }
      row.appendChild(thumb);

      const info = document.createElement("div");
      info.className = "media-info";
      const title = document.createElement("div");
      title.className = "media-name";
      title.textContent = `${KIND_LABELS[it.kind]} ${idx + 1} · ${it.name || "素材"}`;
      info.appendChild(title);

      if (it.kind === "image" && multiImage()) {
        // 批量模式：每张图一条独立提示词 + 独立时长
        const ta = document.createElement("textarea");
        ta.className = "batch-prompt";
        ta.placeholder = "该画面的描述";
        ta.value = it.prompt || "";
        ta.addEventListener("input", () => { it.prompt = ta.value; saveMediaState(); });
        info.appendChild(ta);
        const drow = document.createElement("div");
        drow.className = "batch-dur-row";
        const dl = document.createElement("span");
        dl.className = "media-name";
        dl.textContent = "时长";
        const din = document.createElement("input");
        din.type = "number";
        din.min = "-1";
        din.max = caps.max_duration;
        din.setAttribute("data-tip", `该段时长：-1=智能；或 ${4}~${caps.max_duration} 秒（mini 图生视频最短 4 秒）`);
        din.value = (it.duration == null ? -1 : it.duration);
        din.addEventListener("input", () => { it.duration = parseInt(din.value) || -1; saveMediaState(); });
        din.addEventListener("change", () => { it.duration = parseInt(din.value) || -1; saveMediaState(); });
        drow.append(dl, din);
        info.appendChild(drow);
      } else if (it.kind === "image") {
        const caps = capsFor($("model").value);
        const allowed = caps.roles || ["first_frame", "last_frame", "reference_image"];
        if (!allowed.includes(it.role)) it.role = "first_frame";
        const sel = document.createElement("select");
        sel.className = "media-role";
        sel.setAttribute("data-tip", "图片在视频中的作用：\n· 首帧 = 视频的起始画面（最常见，视频从这张图开始动）\n· 尾帧 = 视频的结束画面；配合首帧可做 A→B 转场（需 2 张图）\n· 参考图 = 只做风格/角色参考，画面自由发挥\n· 注意：首帧/尾帧 与 参考图 不能混用；mini 仅支持首帧");
        for (const [val, label] of Object.entries(ROLE_LABELS)) {
          if (!allowed.includes(val)) continue;
          const opt = document.createElement("option");
          opt.value = val; opt.textContent = label;
          opt.selected = val === it.role;
          sel.appendChild(opt);
        }
        sel.addEventListener("change", () => { it.role = sel.value; adaptParams(); });
        info.appendChild(sel);
      } else if (it.kind === "video") {
        const tag = document.createElement("span");
        tag.className = "media-role-tag";
        tag.textContent = it.local ? "reference_video · 本地上传" : "reference_video";
        info.appendChild(tag);
      } else {
        const tag = document.createElement("span");
        tag.className = "media-role-tag";
        tag.textContent = "reference_audio";
        info.appendChild(tag);
      }
      row.appendChild(info);

      const del = document.createElement("button");
      del.className = "media-del";
      del.textContent = "✕";
      del.title = "移除";
      del.addEventListener("click", () => {
        mediaItems.splice(idx, 1);
        renderMediaList();
      });
      row.appendChild(del);

      list.appendChild(row);
    });
  }

  function mediaLimit() {
    // 批量模式：每张图是独立任务，不受单任务素材上限；单条模式按模型上限
    return multiImage() ? 100 : capsFor($("model").value).max_media;
  }

  function addMedia(kind, fileOrUrl, name) {
    const limit = mediaLimit();
    if (mediaItems.length >= limit) {
      toast(`素材上限 ${limit} 个`, true);
      return;
    }
    if (kind === "image") {
      mediaItems.push({ id: Date.now(), kind, role: "first_frame", url: fileOrUrl, name, prompt: "", duration: -1 });
    } else {
      mediaItems.push({ id: Date.now(), kind, role: kind === "video" ? "reference_video" : "reference_audio", url: fileOrUrl, name });
    }
    renderMediaList();
  }

  $("add-image").addEventListener("click", () => $("image-input").click());
  $("add-audio").addEventListener("click", () => $("audio-input").click());
  $("image-input").addEventListener("change", async (e) => {
    const files = Array.from(e.target.files);
    if (!files.length) return;
    for (const f of files) {
      if (!["image/jpeg", "image/png", "image/webp"].includes(f.type)) { toast(`跳过 ${f.name}：仅支持 jpg/png/webp`, true); continue; }
      if (f.size > 10 * 1024 * 1024) { toast(`跳过 ${f.name}：超过 10MB`, true); continue; }
      if (mediaItems.length >= mediaLimit()) {
        toast(`素材已达上限 ${mediaLimit()} 个`, true);
        break;
      }
      const fd = new FormData();
      fd.append("file", f);
      try {
        const resp = await fetch("/api/upload_image", { method: "POST", body: fd });
        const d = await resp.json();
        if (!resp.ok) throw new Error(d.detail || resp.statusText);
        addMedia("image", "/api/uploads/" + d.filename, f.name);
      } catch (err) { toast(`上传失败 ${f.name}: ` + err.message, true); }
    }
    e.target.value = "";
  });
  $("audio-input").addEventListener("change", (e) => {
    const f = e.target.files[0];
    if (!f) return;
    if (f.size > 15 * 1024 * 1024) { toast("音频不能超过 15MB", true); return; }
    const r = new FileReader();
    r.onload = () => addMedia("audio", r.result, f.name);
    r.readAsDataURL(f);
    e.target.value = "";
  });

  $("add-video").addEventListener("click", () => {
    const url = prompt("输入参考视频的公网 URL（本地文件无法被火山方舟访问，需可公网访问）：", "https://");
    if (!url || url.trim() === "https://") return;
    const t = url.trim();
    if (!/^https?:\/\//i.test(t)) { toast("请输入合法的 http(s) URL", true); return; }
    addMedia("video", t, t.split("/").pop());
  });

  $("upload-video").addEventListener("click", () => $("video-input").click());
  $("video-input").addEventListener("change", async (e) => {
    const f = e.target.files[0];
    if (!f) return;
    if (f.size > 50 * 1024 * 1024) { toast("视频不能超过 50MB", true); return; }
    if (!CFG || !CFG.public_base_url) {
      toast("本地上传视频需要先配置公网隧道：在 config.json 设置 public_base_url（如 ngrok/cloudflared 地址）", true);
      e.target.value = "";
      return;
    }
    const caps = capsFor($("model").value);
    if (mediaItems.length >= mediaLimit()) { toast(`素材上限 ${mediaLimit()} 个`, true); e.target.value = ""; return; }
    const fd = new FormData();
    fd.append("file", f);
    try {
      const resp = await fetch("/api/upload", { method: "POST", body: fd });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || resp.statusText);
      mediaItems.push({ id: Date.now(), kind: "video", role: "reference_video", url: "local://" + data.filename, name: f.name, local: true });
      renderMediaList();
      toast("视频已上传，提交时通过公网隧道地址供方舟访问");
    } catch (err) {
      toast("上传失败: " + err.message, true);
    }
    e.target.value = "";
  });

  /* ================= 参数自适应 ================= */

  function adaptParams() {
    const tt = $("task-type").value;
    const hasFirstLast = mediaItems.some((it) => it.kind === "image" && (it.role === "first_frame" || it.role === "last_frame"));

    // 编辑 / 延长 / 首尾帧 → 必须 adaptive + 智能时长
    const lockRatio = tt === "edit" || tt === "extend" || hasFirstLast;
    const lockDuration = tt === "edit" || tt === "extend";

    ratioLocked = lockRatio;
    durationLocked = lockDuration;

    if (lockRatio) { $("ratio").value = "adaptive"; $("ratio").disabled = true; }
    else $("ratio").disabled = false;

    if (lockDuration) { $("duration").value = "-1"; $("duration").disabled = true; }
    else {
      $("duration").disabled = false;
      const max = capsFor($("model").value).max_duration;
      if (parseInt($("duration").value) > max) $("duration").value = max;
    }
  }

  $("task-type").addEventListener("change", adaptParams);

  function pickTask(t, promptHint) {
    const sel = $("task-type");
    if (![...sel.options].some((o) => o.value === t)) {
      toast("当前模型不支持该任务类型", true);
      return;
    }
    sel.value = t;
    adaptParams();
    const p = $("prompt");
    p.value = p.value ? p.value + "，" + promptHint : promptHint;
    saveMediaState();
    toast("已生成提示词模板，可直接点「开始生成」");
  }
  $("tag-extend").addEventListener("click", () => pickTask("extend", "向后延长 @视频1，延续画面，保持同一风格"));
  $("tag-edit").addEventListener("click", () => pickTask("edit", "编辑 @视频1，"));

  /* ================= 提交生成 ================= */

  /* ================= 提交生成（先确认，再提交） ================= */
  $("generate-btn").addEventListener("click", async () => {
    if (isImageModel($("model").value)) return prepareImage();
    if (multiImage()) return prepareBatch();
    if ($("ext-enabled").checked) return prepareExtend();
      return prepareSingle();
  });
  if (typeof updateExtTunnelHint === "function") updateExtTunnelHint();

  /* ---- 单条视频 ---- */
  function prepareSingle() {
    const prompt = $("prompt").value.trim();
    const content = [];
    if (prompt) content.push({ type: "text", text: prompt });
    for (const it of mediaItems) {
      if (it.kind === "image") content.push({ type: "image_url", image_url: { url: it.url }, role: it.role });
      else if (it.kind === "video") content.push({ type: "video_url", video_url: { url: it.url }, role: "reference_video" });
      else content.push({ type: "audio_url", audio_url: { url: it.url }, role: "reference_audio" });
    }
    if (!content.length) { toast("请填写提示词或添加素材", true); return; }
    const hasMedia = content.some((c) => c.type !== "text");
    if (!hasMedia && !prompt) { toast("请填写提示词或添加素材", true); return; }
    const audioOnly = content.length === 1 && content[0].type === "audio_url";
    if (audioOnly) { toast("音频不能单独使用，需配合图片或视频", true); return; }
    const caps = capsFor($("model").value);
    if (mediaItems.length > caps.max_media) { toast(`素材超过上限 ${caps.max_media} 个`, true); return; }

    const taskType = $("task-type").value;
    const dur = $("duration").disabled ? -1 : (parseInt($("duration").value) || 5);
    if (dur !== -1 && (dur < 4 || dur > caps.max_duration)) {
      toast(`单条时长需为 -1(智能) 或 ${4}~${caps.max_duration} 秒，当前 ${dur} 不合法`, true);
      return;
    }
    const seedVal = parseInt($("seed").value) || -1;
    if (seedVal !== -1 && (seedVal < 0 || seedVal > 2147483647)) {
      toast("seed 需为 -1(随机) 或 0~2147483647", true);
      return;
    }
    const body = {
      model: $("model").value,
      content,
      resolution: $("resolution").value,
      ratio: $("ratio").disabled ? "adaptive" : $("ratio").value,
      duration: dur,
      seed: seedVal,
      camera_fixed: $("camera-fixed").checked,
      watermark: $("watermark").checked,
      generate_audio: $("generate-audio").checked,
      omni_reference_task_type: taskType,
    };

    submitSingle(body);
  }

  async function submitSingle(body) {
    const btn = $("generate-btn");
    btn.disabled = true;
    btn.textContent = "提交中…";
    try {
      const resp = await fetch("/api/tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || resp.statusText);
      toast("已提交，等待排队生成");
      $("prompt").value = "";
      mediaItems = [];
      renderMediaList();
    } catch (err) {
      toast("创建失败: " + err.message, true);
    } finally {
      btn.disabled = false;
      btn.textContent = "✦ 生成";
    }
    refresh();
  }

  /* ---- 图片生成 ---- */
  function prepareImage() {
    const prompt = $("prompt").value.trim();
    if (!prompt) { toast("请先填写图片提示词", true); return; }
    const seq = $("img-seq").checked;
    const n = seq ? 1 : Math.min(4, Math.max(1, parseInt($("img-n").value) || 1));
    const size = $("img-size").value;
    const body = {
      model: $("model").value,
      prompts: Array(n).fill(prompt),
      size,
      watermark: $("img-watermark").checked,
      sequential: seq,
    };
    if (imgRefs.length) body.references = imgRefs;
    submitImage(body);
  }

  async function submitImage(body) {
    try {
      const resp = await fetch("/api/genjob", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const d = await resp.json();
      if (!resp.ok) throw new Error(d.detail || resp.statusText);
      toast("图片任务已提交，去「资产」页查看进度");
      switchTab("assets");
    } catch (err) { toast("提交失败: " + err.message, true); }
    updateImageJobs();
  }

  /* ---- 批量生成（逐条确认） ---- */
  function prepareBatch() {
    const images = mediaItems.filter((it) => it.kind === "image");
    if (!images.length) { toast("请先添加图片", true); return; }
    // 主框多行自动分到每张图（如果还没分）
    const lines = $("prompt").value.split(/\n+/).map((s) => s.trim()).filter(Boolean);
    if (lines.length > 1) {
      images.forEach((img, i) => { if (lines[i]) img.prompt = lines[i].replace(/^\s*\d+[.、)]\s*/, ""); });
      renderMediaList();
    } else if (lines.length === 1) {
      images.forEach((img) => { if (!(img.prompt || "").trim()) img.prompt = lines[0]; });
    }
    for (const it of images) {
      if (!(it.prompt || "").trim()) { toast(`请填写「${it.name}」的描述`, true); return; }
    }
    const globalDur = parseInt($("duration").value) || -1;
    const maxDur = capsFor($("model").value).max_duration;
    const items = images.map((it) => ({
      prompt: (it.prompt || "").trim(),
      image: it.url,
      duration: (it.duration != null && it.duration >= 0) ? it.duration : globalDur,
    }));
    // 校验每条时长：-1(智能) 或 4~max
    for (let i = 0; i < items.length; i++) {
      const dd = items[i].duration;
      if (dd !== -1 && (dd < 4 || dd > maxDur)) {
        toast(`第 ${i + 1} 段时长 ${dd} 不合法：需为 -1(智能) 或 ${4}~${maxDur} 秒`, true);
        return;
      }
    }
    const batchSeed = parseInt($("seed").value) || -1;
    if (batchSeed !== -1 && (batchSeed < 0 || batchSeed > 2147483647)) {
      toast("seed 需为 -1(随机) 或 0~2147483647", true);
      return;
    }
    const body = {
      items,
      model: $("model").value,
      resolution: $("resolution").value,
      duration: -1,
      seed: batchSeed,
      ratio: "adaptive",
      chain: $("chain-toggle").checked,
    };
    submitBatch(body);
  }

  async function submitBatch(body) {
    try {
      await withLoading("启动批量任务…", async () => {
        const resp = await fetch("/api/chain", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.detail || resp.statusText);
        toast(`已启动批量任务：${data.total} 条${data.chain ? "（尾帧衔接）" : ""}`);
      });
    } catch (err) { toast("启动失败: " + err.message, true); }
    updateBatchProgress();
  }

  /* ---------- 长片延长模式 ---------- */
  $("ext-upload-video").addEventListener("click", () => $("ext-video-input").click());
  $("ext-video-input").addEventListener("change", async (e) => {
    const f = e.target.files[0];
    if (!f) return;
    if (f.size > 50 * 1024 * 1024) { toast("视频不能超过 50MB", true); return; }
    const fd = new FormData();
    fd.append("file", f);
    try {
      const resp = await fetch("/api/upload", { method: "POST", body: fd });
      const d = await resp.json();
      if (!resp.ok) throw new Error(d.detail || resp.statusText);
      $("ext-video").value = "local://" + d.filename;
      toast("视频已上传，已填入（local:// 路径）");
    } catch (err) { toast("上传失败: " + err.message, true); }
    e.target.value = "";
  });

  function updateExtTunnelHint() {
    const el = $("ext-tunnel-hint");
    if (!el) return;
    el.textContent = CFG && CFG.public_base_url
      ? "✅ 已配置公网隧道，本地上传视频可被方舟访问。"
      : "⚠ 本地上传视频需在 config.json 配置 public_base_url（公网隧道）才能被方舟访问；否则请填公网 URL。";
  }

  function prepareExtend() {
    const video = $("ext-video").value.trim();
    if (!video) { toast("请填写参考视频 URL（公网或 local://文件名）", true); return; }
    const target = parseInt($("ext-target").value) || 30;
    const round = parseInt($("ext-round").value) || 5;
    const body = {
      model: $("model").value,
      video_url: video,
      prompt: $("ext-prompt").value.trim() || "向后延长 @视频1，保持画风一致，画面连贯",
      target_seconds: target,
      round_seconds: round,
      resolution: $("resolution").value,
      seed: parseInt($("seed").value) || -1,
      watermark: $("watermark").checked,
      generate_audio: $("generate-audio").checked,
    };
    submitExtend(body);
  }

  async function submitExtend(body) {
    try {
      const data = await withLoading("启动延长任务…", async () => {
        const resp = await fetch("/api/extendjob", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        const d = await resp.json();
        if (!resp.ok) throw new Error(d.detail || resp.statusText);
        return d;
      });
      toast(`已启动延长任务：目标 ${data.target_seconds} 秒，最多 ${data.max_rounds} 轮`);
    } catch (err) { toast("启动失败: " + err.message, true); }
    updateExtendStatus();
  }

  async function updateExtendStatus() {
    const el = $("ext-status");
    el.innerHTML = "";
    try {
      const jobs = await (await fetch("/api/extendjobs")).json();
      if (!jobs.length) return;
      for (const j of jobs.slice(0, 3)) {
        const row = document.createElement("div");
        const active = ["queued", "running", "cancelling"].includes(j.status);
        const state = j.status === "done" ? "✅ 完成" : j.status === "cancelled" ? "已停止"
          : j.status === "interrupted" ? "已中断" : j.status === "error" ? "❌ 失败"
          : (j.status === "cancelling" ? "停止中…" : `⏳ 第 ${j.current_round || 0} 轮`);
        row.textContent = `${j.id} ${state} · 累计 ${j.total_duration || 0}/${j.target_seconds} 秒`;
        if (j.error) row.textContent += " · " + j.error.slice(0, 60);
        const b = document.createElement("button");
        b.className = "mini-btn2";
        b.style.cssText = "padding:2px 10px;font-size:11px;margin-left:6px;";
        b.textContent = active ? "⏹" : "🗑";
        b.onclick = async () => {
          await fetch(active ? `/api/extendjobs/${j.id}/stop` : `/api/extendjobs/${j.id}`, { method: "POST" });
          updateExtendStatus();
        };
        row.appendChild(b);
        el.appendChild(row);
      }
    } catch (err) { /* 忽略 */ }
  }

  /* ================= 画廊 ================= */

  const STATUS_LABEL = {
    queued: "排队中", pending: "排队中", running: "生成中",
    succeeded: "已完成", failed: "失败", expired: "已过期", cancelled: "已取消",
  };
  const cardCache = new Map();

  function render(tasks) {
    $("task-count").textContent = `(${tasks.length})`;
    const ids = new Set(tasks.map((t) => t.id));
    for (const [id, c] of cardCache) {
      if (!ids.has(id)) { c.el.remove(); cardCache.delete(id); }
    }
    if (!tasks.length) {
      gallery.innerHTML = `<div class="empty"><div class="big">🎬</div>还没有生成记录<br/>左侧填写提示词、添加素材，点击「开始生成」</div>`;
      return;
    }
    for (const t of tasks) {
      let c = cardCache.get(t.id);
      if (!c) { c = createCard(t); cardCache.set(t.id, c); gallery.appendChild(c.el); }
      else updateCard(c, t);
    }
  }

  function createCard(t) {
    const el = document.createElement("div");
    el.className = "card";
    el.dataset.id = t.id;

    const media = document.createElement("div");
    media.className = "card-media";

    const badge = document.createElement("span");
    badge.className = "status-badge " + t.status;

    const body = document.createElement("div");
    body.className = "card-body";

    const prompt = document.createElement("div");
    prompt.className = "card-prompt";

    const meta = document.createElement("div");
    meta.className = "card-meta";

    const loc = document.createElement("div");
    loc.className = "card-loc";

    const err = document.createElement("div");
    err.className = "card-error";
    err.style.display = "none";

    const actions = document.createElement("div");
    actions.className = "card-actions";
    const dl = document.createElement("a");
    dl.textContent = "下载视频";
    const mv = document.createElement("button");
    mv.textContent = "📦 移动";
    mv.className = "move-card";
    mv.addEventListener("click", (e) => { e.stopPropagation(); openMove("video", t.id, t.prompt || ""); });
    const cut = document.createElement("button");
    cut.textContent = "✂ 截取";
    cut.className = "move-card";
    cut.addEventListener("click", (e) => { e.stopPropagation(); openCut(t.id, t.prompt || ""); });
    const del = document.createElement("button");
    del.className = "del";
    del.textContent = "删除";
    del.addEventListener("click", () => deleteTask(t.id));
    actions.append(dl, mv, cut, del);

    body.append(prompt, meta, loc, err, actions);
    media.appendChild(badge);
    el.append(media, body);

    const c = { el, media, badge, prompt, meta, err, dl, mv, cut, loc, hasVideo: false, spinner: null, imgEl: null };
    const isCut = t.id.startsWith("cut-") || (t.prompt || "").startsWith("✂");
    el.dataset.cat = isCut ? "cut" : "gen";
    updateCard(c, t);
    return c;
  }

  function setMedia(c, t) {
    const hasVideo = !!(t.local_video || t.video_url);
    const active = t.status === "queued" || t.status === "running" || t.status === "pending";

    if (hasVideo && !c.hasVideo) {
      if (c.spinner) { c.spinner.remove(); c.spinner = null; }
      if (c.imgEl) { c.imgEl.remove(); c.imgEl = null; }
      const v = document.createElement("video");
      v.src = t.local_video ? "/api/videos/" + basename(t.local_video) : t.video_url;
      v.controls = true;
      v.preload = "metadata";
      c.media.appendChild(v);
      c.hasVideo = true;
    } else if (!hasVideo && c.hasVideo) {
      const vid = c.media.querySelector("video");
      if (vid) vid.remove();
      c.hasVideo = false;
    }
    if (!hasVideo && !c.imgEl) {
      if (t.image_path) {
        const img = document.createElement("img");
        img.src = "/api/uploads/" + basename(t.image_path);
        img.alt = "";
        c.media.appendChild(img);
        c.imgEl = img;
      } else {
        const ph = document.createElement("div");
        ph.className = "media-ph";
        ph.textContent = "🎬";
        c.media.appendChild(ph);
        c.imgEl = ph;
      }
    }
    if (active && !c.spinner) {
      const sp = document.createElement("div");
      sp.className = "spinner";
      sp.innerHTML = "<i></i>";
      c.media.appendChild(sp);
      c.spinner = sp;
    } else if (!active && c.spinner) {
      c.spinner.remove();
      c.spinner = null;
    }
  }

  function updateCard(c, t) {
    c.badge.className = "status-badge " + t.status;
    c.badge.textContent = STATUS_LABEL[t.status] || t.status;

    c.prompt.textContent = t.prompt || (t.media_count ? `（${t.media_count} 个素材）` : "(无提示词)");

    const pairs = [["模型", t.model], ["类型", (TASK_TYPE_LABELS[t.task_type] || t.task_type || "auto").replace(/\s.*/, "")]];
    if (t.resolution) pairs.push(["分辨率", t.resolution]);
    if (t.ratio) pairs.push(["比例", t.ratio]);
    if (t.duration != null) pairs.push(["时长", t.duration + "s"]);
    c.meta.innerHTML = "";
    for (const [k, v] of pairs) {
      if (!v) continue;
      const tag = document.createElement("span");
      tag.className = "tag";
      tag.textContent = `${k} ${v}`;
      c.meta.appendChild(tag);
    }

    if (t.error) { c.err.textContent = t.error.message || JSON.stringify(t.error); c.err.style.display = ""; }
    else c.err.style.display = "none";
    if (t.moved_to) { c.meta.appendChild((() => { const tag = document.createElement("span"); tag.className = "tag moved"; tag.textContent = "已移动 → " + basename(t.moved_to); return tag; })()); }
    c.mv.style.display = (t.local_video || t.video_url) && !t.moved_to ? "" : "none";
    c.cut.style.display = t.local_video && !t.moved_to ? "" : "none";
    c.loc.innerHTML = "";
    if (t.moved_to) {
      c.loc.innerHTML = `<span class="loc-tag moved">📦 已移动 → ${escapeHtml(relPath(t.moved_to))}</span>`;
    } else if (t.local_video) {
      c.loc.innerHTML = `<span class="loc-tag">📍 ${escapeHtml(relPath(t.local_video))}</span>`;
    } else if (t.video_url) {
      c.loc.innerHTML = `<span class="loc-tag cloud">☁ 云端（未下载本地）</span>`;
    }

    if (t.local_video) { c.dl.href = "/api/videos/" + basename(t.local_video); c.dl.download = t.id + ".mp4"; c.dl.target = "_self"; c.dl.classList.remove("disabled"); }
    else if (t.video_url) { c.dl.href = t.video_url; c.dl.target = "_blank"; c.dl.classList.remove("disabled"); }
    else { c.dl.href = "#"; c.dl.classList.add("disabled"); }

    setMedia(c, t);
  }

  async function deleteTask(id) {
    await withLoading("删除中…", () => fetch("/api/tasks/" + id, { method: "DELETE" }));
    refresh();
  }

  $("clear-all").addEventListener("click", async () => {
    await withLoading("清空中…", async () => {
      const tasks = await (await fetch("/api/tasks")).json();
      for (const t of tasks) await fetch("/api/tasks/" + t.id, { method: "DELETE" });
    });
    refresh();
  });

  /* ================= 轮询 ================= */

  async function updateBatchProgress() {
    try {
      const jobs = await (await fetch("/api/chain")).json();
      const active = jobs.find((j) => ["queued", "running", "cancelling"].includes(j.status));
      const el = $("batch-progress");
      if (active) {
        const pct = active.total ? Math.min(100, Math.round(((active.current_index || 0) / active.total) * 100)) : 0;
        el.hidden = false;
        el.innerHTML = `<div class="bp-text">🎞 批量生成中：${active.current_index || 0}/${active.total}（${active.chain ? "尾帧衔接" : ""}）· <button class="bp-stop" data-id="${active.id}">⏹ 停止</button></div>
          <div class="job-bar"><div class="job-bar-fill" style="width:${pct}%"></div></div>`;
        const stopBtn = el.querySelector(".bp-stop");
        stopBtn.addEventListener("click", async () => {
          await withLoading("停止中…", () => fetch("/api/chain/" + active.id + "/stop", { method: "POST" }));
          toast("已请求停止");
        });
      } else {
        el.hidden = true;
      }
    } catch (err) { /* 忽略 */ }
  }

  /* ---------- 头像 ---------- */
  const AVATAR_KEY = "vs_avatar";
  function loadAvatar() {
    try {
      const data = localStorage.getItem(AVATAR_KEY);
      if (data) {
        $("avatar-img").src = data;
        $("avatar-img").hidden = false;
        $("avatar-placeholder").hidden = true;
      }
    } catch (err) { /* 忽略 */ }
  }
  $("avatar-box").addEventListener("click", (e) => {
    e.stopPropagation();
    $("avatar-menu").hidden = !$("avatar-menu").hidden;
  });
  document.addEventListener("click", () => ($("avatar-menu").hidden = true));
  $("avatar-upload").addEventListener("click", () => $("avatar-input").click());
  $("avatar-as-material").addEventListener("click", () => {
    try {
      const data = localStorage.getItem(AVATAR_KEY);
      if (!data) { toast("还没有头像，先上传一个", true); return; }
      mediaItems.push({ id: Date.now(), kind: "image", role: "first_frame", url: data, name: "我的头像", prompt: "" });
      renderMediaList();
      const ms = $("media-section");
      if (ms) ms.style.display = "";
      toast("头像已加入素材（可作首帧/参考图）");
      switchTab("create");
    } catch (err) { toast("加入素材失败", true); }
  });
  $("avatar-input").addEventListener("change", (e) => {
    const f = e.target.files[0];
    if (!f) return;
    if (f.size > 2 * 1024 * 1024) { toast("头像请小于 2MB", true); return; }
    const reader = new FileReader();
    reader.onload = () => {
      try {
        localStorage.setItem(AVATAR_KEY, reader.result);
        $("avatar-img").src = reader.result;
        $("avatar-img").hidden = false;
        $("avatar-placeholder").hidden = true;
        toast("头像已更新");
      } catch (err) { toast("保存失败：图片过大", true); }
    };
    reader.readAsDataURL(f);
    e.target.value = "";
  });
  loadAvatar();

  /* ---------- 截取视频（ffmpeg） ---------- */
  let cutTaskId = null;
  $("cut-close").addEventListener("click", () => ($("cut-modal").hidden = true));
  $("cut-cancel").addEventListener("click", () => ($("cut-modal").hidden = true));
  function openCut(taskId, label) {
    cutTaskId = taskId;
    $("cut-modal").hidden = false;
    $("cut-item").innerHTML = `<div class="move-res">🎬 <b>${escapeHtml(taskId + ".mp4")}</b></div><div class="move-res-p">${escapeHtml(label || "")}</div>`;
    $("cut-seconds").value = 5;
    $("cut-frames").value = 8;
    document.querySelector('input[name="cut-kind"][value="clip"]').checked = true;
    document.querySelector('input[name="cut-mode"][value="start"]').checked = true;
    updateCutKind();
  }
  document.querySelectorAll('input[name="cut-kind"]').forEach((r) => r.addEventListener("change", updateCutKind));
  function updateCutKind() {
    const frames = document.querySelector('input[name="cut-kind"]:checked').value === "frames";
    $("cut-frames-opt").style.display = frames ? "" : "none";
    $("cut-seconds").closest(".field").style.display = frames ? "none" : "";
  }
  $("cut-ok").addEventListener("click", async () => {
    if (!cutTaskId) return;
    const kind = document.querySelector('input[name="cut-kind"]:checked').value;
    if (kind === "frames") {
      const count = parseInt($("cut-frames").value) || 0;
      if (count < 1) { toast("请填写正确的帧数", true); return; }
      const mode = document.querySelector('input[name="cut-mode"]:checked').value;
      const range = $("cut-range").value.trim();
      try {
        const data = await withLoading("正在抽取帧图…", async () => {
          const resp = await fetch("/api/frames", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ task_id: cutTaskId, count, mode, range }),
          });
          const d = await resp.json();
          if (!resp.ok) throw new Error(d.detail || resp.statusText);
          return d;
        });
        $("cut-modal").hidden = true;
        toast(`已抽取 ${data.results.length} 帧，见资产页「图片任务」`);
        switchTab("assets");
        updateImageJobs();
      } catch (err) { toast("抽帧失败: " + err.message, true); }
      return;
    }
    const mode = document.querySelector('input[name="cut-mode"]:checked').value;
    const seconds = parseInt($("cut-seconds").value) || 0;
    if (seconds < 1) { toast("请填写正确的截取时长", true); return; }
    try {
      const data = await withLoading("正在用 ffmpeg 截取…", async () => {
        const resp = await fetch("/api/cut", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ task_id: cutTaskId, mode, seconds }),
        });
        const d = await resp.json();
        if (!resp.ok) throw new Error(d.detail || resp.statusText);
        return d;
      });
      $("cut-modal").hidden = true;
      toast(`已截取${mode === "start" ? "开头" : "结尾"} ${seconds} 秒，已加入资产`);
      refresh();
    } catch (err) { toast("截取失败: " + err.message, true); }
  });

  function relPath(p) {
    if (!p) return "";
    const s = String(p);
    const idx = s.indexOf("video-studio/");
    return idx >= 0 ? s.slice(idx + "video-studio/".length) : s;
  }

  /* ---------- 资产分类筛选 ---------- */
  function applyAssetFilter(f) {
    const imgSec = $("img-section");
    const vidSec = $("vid-section");
    const batch = $("batch-progress");
    const showImg = f === "all" || f === "img" || f === "frame";
    const showVid = f === "all" || f === "gen" || f === "cut";
    if (imgSec) imgSec.style.display = showImg ? "" : "none";
    if (vidSec) vidSec.style.display = showVid ? "" : "none";
    if (batch) batch.style.display = (f === "img" || f === "frame") ? "none" : "";
    if (imgSec) {
      const head = imgSec.querySelector(".asset-sec-head");
      if (head) {
        const jobs = [...$("image-jobs").querySelectorAll(".img-job")];
        const gen = jobs.filter((el) => el.dataset.cat !== "frame").length;
        const fr = jobs.length - gen;
        head.textContent = `🖼 图片任务（AI生成 ${gen} · 抽帧 ${fr}）`;
      }
    }
    document.querySelectorAll("#gallery .card").forEach((el) => {
      const cat = el.dataset.cat || "gen";
      el.style.display = (f === "all" || cat === f) ? "" : "none";
    });
    document.querySelectorAll("#image-jobs .img-job").forEach((el) => {
      const cat = el.dataset.cat || "gen";
      const want = f === "all" || (f === "img" ? cat === "gen" : cat === f);
      el.style.display = want ? "" : "none";
    });
    document.querySelectorAll(".asset-filter").forEach((b) => b.classList.toggle("active", b.dataset.f === f));
  }
  document.querySelectorAll(".asset-filter").forEach((b) => b.addEventListener("click", () => {
    localStorage.setItem("vs_asset_filter", b.dataset.f);
    applyAssetFilter(b.dataset.f);
  }));
  (function initFilter() {
    let f = "all";
    try { f = localStorage.getItem("vs_asset_filter") || "all"; } catch (err) {}
    applyAssetFilter(f);
  })();

  function openLightbox(src) {
    const lb = $("lightbox");
    $("lightbox-img").src = src;
    lb.hidden = false;
  }
  (function initLightbox() {
    const lb = $("lightbox");
    if (!lb) return;
    lb.addEventListener("click", () => { lb.hidden = true; });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") lb.hidden = true; });
  })();

  /* ---------- 移动资源（每卡片，视频/图片通用，服务端文件夹浏览器） ---------- */
  let moveTarget = null; // {kind: "video"|"file", name: string}
  let moveCurPath = "";
  $("move-close").addEventListener("click", () => ($("move-modal").hidden = true));
  $("move-cancel").addEventListener("click", () => ($("move-modal").hidden = true));

  async function loadBrowse(path) {
    try {
      const d = await (await fetch("/api/fs/browse?path=" + encodeURIComponent(path))).json();
      moveCurPath = d.path;
      $("move-path").textContent = d.path;
      const up = $("move-up-row");
      up.innerHTML = d.parent ? `<button class="pill-btn" id="move-up">⬆ ${d.name === "lzf" ? "上级" : "上级"}</button>` : "";
      const ub = $("move-up");
      if (ub) ub.addEventListener("click", () => loadBrowse(d.parent));
      const fl = $("move-folders");
      if (!d.subdirs.length) { fl.innerHTML = "<div class='move-empty'>（此目录下没有子文件夹，可直接移动到当前目录）</div>"; return; }
      fl.innerHTML = d.subdirs.map((s) => `<button class="move-folder" data-path="${encodeURIComponent(d.path + "/" + s)}">📁 ${escapeHtml(s)}</button>`).join("");
      fl.querySelectorAll(".move-folder").forEach((b) => b.addEventListener("click", () => loadBrowse(decodeURIComponent(b.dataset.path))));
    } catch (err) {
      $("move-folders").innerHTML = "<div class='move-empty'>加载失败</div>";
    }
  }

  async function openMove(kind, name, label) {
    moveTarget = { kind, name };
    $("move-modal").hidden = false;
    $("move-item").innerHTML = `<div class="move-res">${kind === "video" ? "🎬" : "🖼"} <b>${escapeHtml(name + (kind === "video" ? ".mp4" : ""))}</b></div><div class="move-res-p">${escapeHtml(label || "")}</div>`;
    loadBrowse("");
  }

  async function openJobMove(jobId) {
    const jobs = await (await fetch("/api/genjobs")).json();
    const j = jobs.find((x) => x.id === jobId);
    if (!j || !(j.results || []).length) { toast("该任务没有可移动的图片", true); return; }
    moveTarget = { kind: "files", name: j.results.length + " 张图片", names: j.results.map((r) => r.filename) };
    $("move-modal").hidden = false;
    $("move-item").innerHTML = `<div class="move-res">🖼 <b>${j.results.length} 张图片</b></div><div class="move-res-p">任务 ${escapeHtml(jobId)}</div>`;
    loadBrowse("");
  }

  $("move-ok").addEventListener("click", async () => {
    if (!moveTarget || !moveCurPath) return;
    const body = moveTarget.kind === "video"
      ? { videos: [moveTarget.name], files: [], dest: moveCurPath }
      : moveTarget.kind === "files"
        ? { videos: [], files: moveTarget.names, dest: moveCurPath }
        : { videos: [], files: [moveTarget.name], dest: moveCurPath };
    try {
      const resp = await fetch("/api/move", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const d = await resp.json();
      if (!resp.ok) throw new Error(d.detail || resp.statusText);
      $("move-modal").hidden = true;
      if (d.errors.length) toast("移动失败: " + d.errors[0], true);
      else toast(`已移动 ${d.moved.length} 个文件 → ${moveCurPath}`);
      refresh();
      updateImageJobs();
    } catch (err) { toast("移动失败: " + err.message, true); }
  });

  let lastImgJobsSig = "";
  async function updateImageJobs() {
    const el = $("image-jobs");
    if (!el) return;
    try {
      const jobs = await (await fetch("/api/genjobs")).json();
      const sig = JSON.stringify(jobs);
      if (sig === lastImgJobsSig) return;
      lastImgJobsSig = sig;
      if (!jobs.length) { el.innerHTML = ""; return; }
      const STATUS = { queued: "排队中", running: "生成中", cancelling: "取消中", done: "已完成", cancelled: "已取消", interrupted: "已中断" };
      el.innerHTML = jobs.map((j) => {
        const pct = j.total ? Math.min(100, Math.round(((j.current || 0) / j.total) * 100)) : 0;
        const st = STATUS[j.status] || j.status;
        const active = ["queued", "running", "cancelling"].includes(j.status);
        const imgs = (j.results || []).map((r) => `<div class="img-job-item">
            <label class="img-sel-box"><input type="checkbox" class="img-sel" data-fn="${r.filename}" /><span class="img-sel-mark">✓</span></label>
            <img src="/api/uploads/${r.filename}" alt="" />
            <div class="img-job-name">${r.prompt ? escapeHtml(r.prompt.slice(0, 24)) : ""}</div>
          </div>`).join("");
        const isFrame = j.kind === "frame" ||
          (!j.kind && ((j.prompts && /^从 .*帧/.test(j.prompts[0])) || (j.results && j.results[0] && /^帧 \d/.test(j.results[0].prompt || ""))));
        const cat = isFrame ? "frame" : "gen";
        const locCount = (j.results || []).length;
        return `<div class="img-job ${active ? "active" : ""}" data-cat="${cat}">
          <div class="img-job-head">
            <span>${st}${active ? ` ${j.current || 0}/${j.total}` : ""}</span>
            <span class="img-job-actions">
              ${active ? `<button class="bp-stop" data-id="${j.id}">⏹ 停止</button>` : ""}
              ${j.status === "done" && imgs ? `<button class="bp-add" data-id="${j.id}">＋ 加入素材</button><button class="bp-move" data-id="${j.id}">📦 移动</button>` : ""}
              <button class="bp-del" data-id="${j.id}">✕</button>
            </span>
          </div>
          <div class="img-job-loc"><span class="loc-tag ${isFrame ? "frame" : "gen"}">${isFrame ? "🎞 抽帧" : "🖼 AI生成"} · 📍 data/uploads/（${locCount} 张）</span></div>
          ${active ? `<div class="job-bar"><div class="job-bar-fill" style="width:${pct}%"></div></div>` : ""}
          ${j.error ? `<div class="img-job-error">${escapeHtml(j.error)}</div>` : ""}
          ${imgs ? `<div class="img-job-grid">${imgs}</div>` : ""}
        </div>`;
      }).join("");
      el.querySelectorAll(".img-job-item img").forEach((im) => im.addEventListener("click", () => openLightbox(im.src)));
      el.querySelectorAll(".img-sel").forEach((cb) => cb.addEventListener("change", () => {
        cb.closest(".img-job-item").classList.toggle("sel", cb.checked);
      }));
      el.querySelectorAll(".bp-stop").forEach((b) => b.addEventListener("click", async () => {
        await fetch("/api/genjobs/" + b.dataset.id + "/stop", { method: "POST" });
        toast("已请求停止");
        updateImageJobs();
      }));
      el.querySelectorAll(".bp-del").forEach((b) => b.addEventListener("click", async () => {
        await fetch("/api/genjobs/" + b.dataset.id, { method: "DELETE" });
        updateImageJobs();
      }));
      el.querySelectorAll(".bp-add").forEach((b) => b.addEventListener("click", async () => {
        const box = b.closest(".img-job");
        const checked = [...box.querySelectorAll(".img-sel:checked")].map((c) => c.dataset.fn);
        if (!checked.length) { toast("请先勾选要加入素材的图片", true); return; }
        checked.forEach((fn, i) => {
          mediaItems.push({ id: Date.now() + i, kind: "image", role: "first_frame", url: "/api/uploads/" + fn, name: "生成图 " + (i + 1), prompt: "" });
        });
        renderMediaList();
        const ms = $("media-section");
        if (ms) ms.style.display = "";
        toast(`已加入 ${checked.length} 张到素材`);
        switchTab("create");
        if (ms) ms.scrollIntoView({ behavior: "smooth", block: "center" });
      }));
      el.querySelectorAll(".bp-move").forEach((b) => b.addEventListener("click", async (e) => { e.stopPropagation(); await openJobMove(b.dataset.id); }));
    } catch (err) { /* 忽略 */ }
  }

  async function refresh() {
    try {
      const tasks = await (await fetch("/api/tasks")).json();
      render(tasks);
      setConn(true);
      updateImageJobs();
      applyAssetFilter(document.querySelector(".asset-filter.active").dataset.f);
    } catch (err) {
      setConn(false);
    }
    updateBatchProgress();
    if (typeof updateExtendStatus === "function") updateExtendStatus();
  }

  function setConn(ok) {
    $("conn-dot").className = "dot " + (ok ? "ok" : "bad");
    $("conn-text").textContent = ok ? "服务正常" : "连接异常";
  }

  pollTimer = setInterval(refresh, 3000);
  refresh();
  loadConfig();

  function basename(p) { return p.split("/").pop(); }

  /* ---------- chips（快捷示例） ---------- */
  document.querySelectorAll("#chips .chip, .tip-block .chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const fill = chip.dataset.fill || chip.textContent;
      $("prompt").value = $("prompt").value ? $("prompt").value + "，" + fill : fill;
      saveMediaState();
      toast("已加入提示词：" + fill.slice(0, 24) + "…");
    });
  });

  /* ---------- 顶部标签导航 ---------- */
  const TAB_KEY = "vs_active_tab";
  function switchTab(v) {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    const tb = document.querySelector(`.tab[data-view="${v}"]`);
    if (tb) tb.classList.add("active");
    ["create", "assets", "usage", "cap"].forEach((k) => ($("view-" + k).hidden = k !== v));
    if (v === "usage") loadUsage();
    if (v === "assets") { updateBatchProgress(); updateImageJobs(); }
    if (v === "cap") renderCaps();
    try { localStorage.setItem(TAB_KEY, v); } catch (err) {}
  }
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => switchTab(tab.dataset.view));
  });
  // 刷新后停留在上次的标签页
  (function restoreTab() {
    try {
      const saved = localStorage.getItem(TAB_KEY);
      if (saved && ["create", "assets", "usage", "cap"].includes(saved)) switchTab(saved);
    } catch (err) {}
  })();

  /* ---------- 能力页 ---------- */
  const CAP_LABEL = {
    input: { text: "文本", image: "图片", video: "视频", audio: "音频" },
    task: { auto: "自动判断", text: "文生视频", image: "图生视频", edit: "视频编辑", extend: "视频延长" },
    role: { first_frame: "首帧图", last_frame: "尾帧图", reference_image: "参考图" },
  };
  const IMG_CAPS = {
    "doubao-seedream-5-0-pro-260628": ["文生图", "图生图（参考图）", "最高画质", "多尺寸比例", "可加水印", "不支持组图"],
    "doubao-seedream-5-0-260128": ["文生图", "图生图（参考图）", "组图（一次多条关联图）", "性价比高", "可加水印"],
  };

  function capVal(caps, k) {
    const v = caps[k];
    if (k === "inputs") return (v || []).map((x) => CAP_LABEL.input[x] || x).join(" / ") || "—";
    if (k === "task_types") return (v || []).map((x) => CAP_LABEL.task[x] || x).join("、") || "—";
    if (k === "roles") return (v || []).map((x) => CAP_LABEL.role[x] || x).join("、") || "—";
    if (k === "camera_fixed") return v ? "画面可运动" : "固定镜头";
    if (k === "max_media") return (v == null ? "—" : v + " 个");
    if (k === "max_duration") return (v == null ? "—" : "4-" + v + " 秒");
    if (k === "resolutions") return (v || []).join(" / ") || "—";
    return v == null ? "—" : String(v);
  }

  function renderCaps() {
    const el = $("cap-content");
    if (!el) return;
    if (!CFG) { el.innerHTML = "<div class='empty'>配置加载中…</div>"; return; }
    const caps = CFG.model_caps || {};
    const models = CFG.models || {};
    const ids = Object.keys(caps);
    const ROWS = [
      ["resolutions", "分辨率"], ["max_duration", "单段时长"], ["inputs", "输入模态"],
      ["task_types", "任务类型"], ["roles", "帧图 / 参考图"], ["camera_fixed", "画面运动"],
      ["max_media", "素材上限"],
    ];
    let html = `<div class="cap-note">以下基于当前 config.json 的能力配置生成。模型按列对照，勾 ✓ 表示支持 / ✗ 不支持。</div>
    <div class="cap-block"><h3>🎬 图生视频 / 文生视频模型</h3>
    <table class="cap-table"><thead><tr><th>能力项</th>${ids.map((id) => `<th>${escapeHtml(models[id] || id)}</th>`).join("")}</tr></thead><tbody>`;
    ROWS.forEach(([k, l]) => {
      html += `<tr><td class="cap-row-name">${l}</td>${ids.map((id) => `<td>${capVal(caps[id], k)}</td>`).join("")}</tr>`;
    });
    // 支持与否布尔项
    const BOOL_ROWS = [
      ["文生视频", "t2v"], ["首帧图生", "i2v"], ["尾帧图生", "last"], ["参考图", "refimg"],
      ["参考视频/音频", "refav"], ["@图片N 语法", "atsign"], ["分镜脚本参考(R2V)", "r2v"],
      ["视频编辑", "edit"], ["视频延长", "extend"], ["多轮延长", "extendx"],
      ["双声道音频", "stereo"], ["联网搜索", "search"],
    ];
    html += `<tr><td class="cap-row-name">文生视频</td>${ids.map((id) => `<td>${(caps[id].task_types || []).includes("text") || (caps[id].inputs || []).includes("text") ? "✓" : "✗"}</td>`).join("")}</tr>`;
    html += `<tr><td class="cap-row-name">首帧图生</td>${ids.map((id) => `<td>${(caps[id].roles || []).includes("first_frame") ? "✓" : "✗"}</td>`).join("")}</tr>`;
    html += `<tr><td class="cap-row-name">尾帧图生</td>${ids.map((id) => `<td>${(caps[id].roles || []).includes("last_frame") ? "✓" : "✗"}</td>`).join("")}</tr>`;
    html += `<tr><td class="cap-row-name">参考图</td>${ids.map((id) => `<td>${(caps[id].roles || []).includes("reference_image") ? "✓" : "✗"}</td>`).join("")}</tr>`;
    html += `<tr><td class="cap-row-name">参考视频/音频</td>${ids.map((id) => `<td>${(caps[id].inputs || []).includes("video") || (caps[id].inputs || []).includes("audio") ? "✓" : "✗"}</td>`).join("")}</tr>`;
    html += `<tr><td class="cap-row-name">@图片N 引用语法</td>${ids.map((id) => `<td>${(caps[id].inputs || []).includes("video") ? "✓" : "✗"}</td>`).join("")}</tr>`;
    html += `<tr><td class="cap-row-name">视频编辑</td>${ids.map((id) => `<td>${(caps[id].task_types || []).includes("edit") ? "✓" : "✗"}</td>`).join("")}</tr>`;
    html += `<tr><td class="cap-row-name">视频延长</td>${ids.map((id) => `<td>${(caps[id].task_types || []).includes("extend") ? "✓" : "✗"}</td>`).join("")}</tr>`;
    html += `<tr><td class="cap-row-name">画面运动</td>${ids.map((id) => `<td>${caps[id].camera_fixed ? "✓" : "✗"}</td>`).join("")}</tr>`;
    html += `</tbody></table></div>`;

    // 特征标签
    html += `<div class="cap-block"><h3>模型特征摘要</h3>`;
    ids.forEach((id) => {
      html += `<div class="cap-model"><b>${escapeHtml(models[id] || id)}</b><div class="cap-chips">${(caps[id].features || []).map((f) => `<span class="cap-chip">${escapeHtml(f)}</span>`).join("")}</div></div>`;
    });
    html += `</div>`;

    // 图片模型
    const imgIds = Object.keys(CFG.image_models || {});
    const IMG_ROWS = [
      ["定位", { pro: "最强画质", lite: "性价比首选" }],
      ["文生图", { pro: true, lite: true }],
      ["图生图（参考图）", { pro: true, lite: true }],
      ["组图（一条提示词出多张关联图）", { pro: false, lite: "✓（≤15 张）" }],
      ["尺寸下限", { pro: "≥3,686,400 像素", lite: "≥3,686,400 像素" }],
      ["多尺寸比例", { pro: true, lite: true }],
      ["水印开关", { pro: true, lite: true }],
      ["成本", { pro: "高（质量优先）", lite: "低（批量划算）" }],
      ["适用场景", { pro: "封面/海报/正式出图", lite: "分镜配图/批量试错" }],
    ];
    const proId = imgIds.find((id) => id.includes("pro")) || imgIds[0];
    const liteId = imgIds.find((id) => !id.includes("pro")) || imgIds[1] || imgIds[0];
    const imgNames = { pro: CFG.image_models[proId] || "Seedream pro", lite: CFG.image_models[liteId] || "Seedream lite" };
    html += `<div class="cap-block"><h3>🖼 文生图 / 图生图模型（Seedream 5.0）</h3>
    <table class="cap-table"><thead><tr><th>能力项</th><th>${escapeHtml(imgNames.pro)}</th><th>${escapeHtml(imgNames.lite)}</th></tr></thead><tbody>`;
    IMG_ROWS.forEach(([l, m]) => {
      const fmt = (v) => v === true ? "✓" : (v === false ? "✗" : escapeHtml(String(v)));
      html += `<tr><td class="cap-row-name">${l}</td><td>${fmt(m.pro)}</td><td>${fmt(m.lite)}</td></tr>`;
    });
    html += `</tbody></table></div>`;
    html += `<div class="cap-block"><h3>图片模型列表</h3>`;
    imgIds.forEach((id) => {
      const label = CFG.image_models[id];
      const items = IMG_CAPS[id] || ["文生图"];
      html += `<div class="cap-model"><b>${escapeHtml(label)}</b><span class="cap-id">${escapeHtml(id)}</span><div class="cap-chips">${items.map((f) => `<span class="cap-chip">${escapeHtml(f)}</span>`).join("")}</div></div>`;
    });
    html += `<div class="cap-note">※ 图片尺寸需 ≥ 3,686,400 像素（如 2560×1440），Seedream 5.0 最低像素要求。组图仅在 Seedream 5.0 lite 支持（界面会自动隐藏/显示）。</div>`;
    html += `</div>`;
    html += `<div class="cap-note">⚠ 2.0 / 2.5 需在方舟控制台开通模型权限；若调用报 ModelNotOpen，说明尚未开通。</div>`;
    el.innerHTML = html;
  }
  async function loadUsage() {
    const body = $("usage-body");
    body.innerHTML = "加载中…";
    try {
      const [usageResp, balResp] = await Promise.all([
        fetch("/api/usage?days=7"),
        fetch("/api/balance"),
      ]);
      const usage = await usageResp.json();
      let balanceHtml = "";
      if (balResp.ok) {
        const b = await balResp.json();
        const avail = parseFloat(b.AvailableBalance || "0").toFixed(2);
        const freeze = parseFloat(b.FreezeAmount || "0").toFixed(2);
        const arrears = parseFloat(b.ArrearsBalance || "0").toFixed(2);
        balanceHtml = `<div class="balance-bar">💳 账户可用余额：<b class="balance-num">¥${avail}</b>${freeze !== "0.00" ? `（冻结 ¥${freeze}）` : ""}${arrears !== "0.00" ? `（欠费 ¥${arrears}）` : ""}</div>`;
      }
      if (!usageResp.ok) throw new Error(usage.detail || usageResp.statusText);
      body.innerHTML = balanceHtml + renderUsageHtml(usage);
    } catch (err) {
      body.innerHTML = `
        <div class="usage-msg">查询失败：${escapeHtml(err.message)}</div>
        <div class="usage-tip">需要先在 config.json 配置火山引擎 AK/SK：
          <br/>· <code>access_key_id</code>：AccessKey ID
          <br/>· <code>secret_access_key</code>：Secret Access Key
          <br/>· <code>usage_apikey_id</code>（可选）：API Key 的「资源 ID」
          <br/>获取：控制台 → 访问控制 → 密钥管理（AK/SK）；API Key 管理页（资源 ID）
        </div>`;
    }
  }

  function renderUsageHtml(data) {
    const rows = data.rows || [];
    const total = rows.reduce((s, r) => s + (parseInt(r.TotalTokens) || 0), 0);
    const paid = rows.filter((r) => r.BillingStatus === "normal").reduce((s, r) => s + (parseInt(r.TotalTokens) || 0), 0);
    const free = rows.filter((r) => r.BillingStatus && r.BillingStatus !== "normal").reduce((s, r) => s + (parseInt(r.TotalTokens) || 0), 0);

    let html = `
      <div class="usage-summary">
        <div class="us-card"><span class="us-num">${total.toLocaleString()}</span><span class="us-label">总 Token（${data.start} ~ ${data.end}）</span></div>
        <div class="us-card"><span class="us-num" style="color:var(--green)">${paid.toLocaleString()}</span><span class="us-label">付费余额消耗</span></div>
        <div class="us-card"><span class="us-num" style="color:var(--yellow)">${free.toLocaleString()}</span><span class="us-label">安心体验/免费消耗</span></div>
      </div>`;

    if (!rows.length) {
      html += `<div class="usage-msg">这段时间内暂无用量数据。</div>`;
    } else {
      html += `<table class="usage-table"><thead><tr><th>日期</th><th>计费类型</th><th>总Token</th><th>请求数</th></tr></thead><tbody>`;
      for (const r of rows) {
        html += `<tr>
          <td>${escapeHtml(r.Day || "")}${r.Hour ? " " + escapeHtml(String(r.Hour)) + ":00" : ""}</td>
          <td><span class="bill ${r.BillingStatus === "normal" ? "paid" : "free"}">${escapeHtml(r.BillingStatusLabel || r.BillingStatus || "-")}</span></td>
          <td>${(parseInt(r.TotalTokens) || 0).toLocaleString()}</td>
          <td>${parseInt(r.ReqCnt) || 0}</td>
        </tr>`;
      }
      html += `</tbody></table>`;
    }
    return html;
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function imageSizeForRatio(ratio) {
    const map = {
      "16:9": "2560x1440", "9:16": "1440x2560", "4:3": "2304x1728",
      "3:4": "1728x2304", "1:1": "2048x2048", "21:9": "3024x1296", "adaptive": "2560x1440",
    };
    return map[ratio] || "2560x1440";
  }

  /* ---------- 单图模板载入（single_prompts.json） ---------- */
  $("load-single-prompts").addEventListener("click", async () => {
    try {
      const resp = await fetch("/api/single_prompts");
      const d = await resp.json();
      if (!resp.ok) throw new Error(d.detail || resp.statusText);
      const items = d.items || [];
      if (!items.length) { toast("single_prompts.json 为空或不存在", true); return; }
      $("tpl-list").innerHTML = items.map((it, i) => `
        <button class="tpl-row" data-i="${i}">
          <b>${escapeHtml(it.name)}</b>
          <span>${escapeHtml(it.prompt.slice(0, 90))}${it.prompt.length > 90 ? "…" : ""}</span>
        </button>`).join("");
      $("tpl-modal").hidden = false;
      $("tpl-list").querySelectorAll(".tpl-row").forEach((b) => b.addEventListener("click", () => {
        const it = items[+b.dataset.i];
        $("prompt").value = it.prompt;
        saveMediaState();
        $("tpl-modal").hidden = true;
        toast(`已载入模板「${it.name}」`);
      }));
    } catch (err) { toast("载入失败: " + err.message, true); }
  });
  $("tpl-close").addEventListener("click", () => ($("tpl-modal").hidden = true));

  /* ---------- 批量模式（内嵌左侧面板） ---------- */
  $("load-story-prompts").addEventListener("click", async () => {
    const images = mediaItems.filter((it) => it.kind === "image");
    if (!images.length) { toast("请先上传图片，再载入", true); return; }
    try {
      const resp = await fetch("/api/story_prompts");
      const d = await resp.json();
      if (!resp.ok) throw new Error(d.detail || resp.statusText);
      const items = d.items || [];
      if (!items.length) { toast("story_prompts.json 为空或不存在", true); return; }
      // 动态更新按钮条数（不写死）
      $("load-story-prompts").textContent = `📖 载入 story_prompts（${items.length} 条，按顺序填入每张图）`;
      let filled = 0;
      images.forEach((img, i) => {
        if (!items[i]) return;
        img.prompt = items[i].prompt;
        // 从提示词文本里解析时长（如 "8秒"）自动填入时长框
        const m = items[i].prompt.match(/(\d+)\s*秒/);
        if (m) {
          const v = parseInt(m[1]);
          if (v >= 4 && v <= capsFor($("model").value).max_duration) img.duration = v;
        }
        filled++;
      });
      renderMediaList();
      toast(`已按顺序填入 ${filled} 张图的分镜提示词（含时长）`);
    } catch (err) { toast("载入失败: " + err.message, true); }
  });

  function updateMultiUI() {
    const m = multiImage();
    const ct = $("chain-toggle-wrap");
    if (ct) ct.hidden = !m;
    const lp = $("load-story-prompts");
    if (lp) lp.hidden = !m;
    const lsp = $("load-single-prompts");
    if (lsp) lsp.hidden = m;
    const mh = $("multi-hint");
    if (mh) mh.hidden = !m;
  }

  function updateHeroForBatch() {
    // 批量模式下全局时长框作为所有段默认时长（每段独立框可覆盖）
  }

  $("apply-storyboard").addEventListener("click", applyStoryboard);
  function applyStoryboard() {
    const images = mediaItems.filter((it) => it.kind === "image");
    if (!images.length) { toast("请先在左侧添加图片", true); return; }
    const text = $("prompt").value;
    // 按编号行或普通行切分
    let lines = text.split(/\n+/).map((s) => s.trim()).filter(Boolean);
    if (lines.length) {
      // 去掉编号前缀（如 "1. " / "1、"）
      lines = lines.map((l) => l.replace(/^\s*\d+[.、)]\s*/, ""));
      images.forEach((img, i) => { if (lines[i]) img.prompt = lines[i]; });
      renderMediaList();
      toast(`已按顺序填入 ${Math.min(lines.length, images.length)} 张图（可逐张微调）`);
    } else {
      toast("主框没有内容可应用", true);
    }
  }

  /* 图片模式：参考图（图生图）管理 */
  let imgRefs = [];
  $("img-ref-add").addEventListener("click", () => $("img-ref-input").click());
  $("img-ref-input").addEventListener("change", (e) => {
    const files = Array.from(e.target.files);
    files.forEach((f) => {
      if (!["image/jpeg", "image/png", "image/webp"].includes(f.type)) return;
      const r = new FileReader();
      r.onload = () => { imgRefs.push(r.result); renderImgRefList(); };
      r.readAsDataURL(f);
    });
    e.target.value = "";
  });
  function renderImgRefList() {
    const list = $("img-ref-list");
    list.innerHTML = "";
    if (!imgRefs.length) {
      list.innerHTML = `<div class="media-empty">无参考图（纯文生图）。添加后可做图生图/风格融合。</div>`;
      return;
    }
    imgRefs.forEach((src, idx) => {
      const row = document.createElement("div");
      row.className = "media-item";
      const th = document.createElement("div");
      th.className = "media-thumb";
      const img = document.createElement("img");
      img.src = src;
      th.appendChild(img);
      row.appendChild(th);
      const info = document.createElement("div");
      info.className = "media-info";
      const nm = document.createElement("div");
      nm.className = "media-name";
      nm.textContent = "参考图 " + (idx + 1);
      info.appendChild(nm);
      row.appendChild(info);
      const del = document.createElement("button");
      del.className = "media-del";
      del.textContent = "✕";
      del.addEventListener("click", () => { imgRefs.splice(idx, 1); renderImgRefList(); });
      row.appendChild(del);
      list.appendChild(row);
    });
  }

  /* ---------- toast / 全局转圈 ---------- */
  function toast(msg, isError) {
    const el = document.createElement("div");
    el.className = "toast" + (isError ? " error" : "");
    el.textContent = msg;
    $("toasts").appendChild(el);
    setTimeout(() => el.remove(), 4000);
  }

  let loadingCount = 0;
  function showLoading(msg) {
    loadingCount++;
    $("loading-msg").textContent = msg || "处理中…";
    $("global-loading").hidden = false;
  }
  function hideLoading() {
    loadingCount = Math.max(0, loadingCount - 1);
    if (loadingCount === 0) $("global-loading").hidden = true;
  }
  async function withLoading(msg, fn) {
    showLoading(msg);
    try { return await fn(); }
    finally { hideLoading(); }
  }

  /* ---------- 自定义气泡提示 ---------- */
  const tooltipEl = $("tooltip");
  function showTooltip(el) {
    const text = (el.getAttribute("data-tip") || "").replace(/\\n/g, "\n");
    if (!text) return;
    tooltipEl.textContent = text;
    tooltipEl.hidden = false;
    const r = el.getBoundingClientRect();
    const tw = tooltipEl.offsetWidth || 320;
    let left = r.left + r.width / 2;
    left = Math.max(tw / 2 + 8, Math.min(left, window.innerWidth - tw / 2 - 8));
    tooltipEl.style.left = left + "px";
    if (r.top < 150) {
      tooltipEl.style.top = (r.bottom + 10) + "px";
      tooltipEl.style.transform = "translate(-50%, 0)";
    } else {
      tooltipEl.style.top = (r.top - 10) + "px";
      tooltipEl.style.transform = "translate(-50%, -100%)";
    }
  }
  function hideTooltip() { tooltipEl.hidden = true; }
  document.addEventListener("mouseover", (e) => {
    const t = e.target.closest("[data-tip]");
    if (t) showTooltip(t);
  });
  document.addEventListener("mouseout", (e) => {
    if (e.target.closest("[data-tip]")) hideTooltip();
  });
})();