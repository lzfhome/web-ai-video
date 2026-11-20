# cine/vendor

第三方运行时。目前只有 three.js。

| 文件 | 来源 | 许可 |
|---|---|---|
| `three.module.min.js` | three.js | MIT |
| `three.core.min.js` | three.js | MIT |

## 用法

`cine/video/engines/dom/index.html` 里用 importmap 指过来：

```html
<script type="importmap">
{ "imports": { "three": "/cine/vendor/three.module.min.js" } }
</script>
```

业务代码只写 `import * as THREE from "three"`，不要写相对路径。

## 升级

替换两个文件即可，注意版本要一致（`three.module` 和 `three.core` 同一个 release）。
升级后跑一次 `python tools/smoke_test.py` 和任意一条 DOM 产线。
