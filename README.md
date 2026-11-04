# KYC

Mia Li 的个人网站，静态壳。视觉还没定，这一版只有页面和可以替换的文字。

## 页面

- `/` 首页
- `/about` 关于
- `/experience` 体验

首页和关于页是语义 HTML 和一份全局 CSS，几乎没有 JavaScript。
体验页是空房间。动效和小游戏以后只放在这里，不要放进首页、关于页或共用布局。

## 本地运行

需要 Node.js 22.23.4 或更高。

```bash
npm install
npm run dev
```

构建静态文件：

```bash
npm run build
npm run preview
```

产物在 `dist/`。

## 体验页以后怎么加东西

挂载点是 `#experience-mount`，组件在 `src/components/ExperienceSlot.astro`，只由 `src/pages/experience.astro` 使用。

1. 作品单独一个模块，例如 `src/experience/pieces/<name>.ts`。
2. 只在体验页里动态 `import()`，或使用一个只出现在这一页的 Astro island，让这段代码不进入首页和关于页。
3. 打开体验页之后再启动。
4. 离开页面时停掉：在 `pagehide` 里取消动画帧、断开观察器、移除监听，并释放音频或游戏循环。
5. 先看 `prefers-reduced-motion` 再决定要不要动。`src/styles/global.css` 里已经有这条规则。

一次只挂一件。换下一件之前，先卸掉当前的。
