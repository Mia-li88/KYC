import { defineConfig } from 'astro/config';

// Static HTML. Do not add view transitions or a client router here —
// those inject JavaScript on every page, including home and about.
export default defineConfig({
  output: 'static',
  build: {
    inlineStylesheets: 'always',
  },
});
