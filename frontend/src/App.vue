<template>
  <a href="#main" class="skip-link">{{ $t('common.skipToContent') }}</a>
  <router-view />
</template>

<script setup>
// Routing only. Design tokens, fonts and global resets live in
// src/main.js (which imports design/tokens.css + typography.css +
// components.css). The legacy globals previously here were pinning the
// font and palette to dark/mono and clashed with the warm-paper system.
</script>

<style>
/* Lightweight global reset: keep box-sizing + margin reset only.
   Body font-family / color come from design/tokens.css. */
* { box-sizing: border-box; }

/* — Skip link for keyboard / screen-reader users — */
.skip-link {
  position: absolute;
  top: -100px;
  left: 12px;
  z-index: 1000;
  background: var(--ink);
  color: var(--bg);
  padding: 8px 14px;
  border-radius: var(--r-sm);
  text-decoration: none;
  font-family: var(--mono);
  font-size: 12px;
  letter-spacing: 0.04em;
  transition: top 0.18s;
}
.skip-link:focus { top: 12px; outline: 2px solid var(--signal); outline-offset: 2px; }

/* Custom scrollbar tuned to the warm paper palette. */
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: var(--surface-2); }
::-webkit-scrollbar-thumb {
  background: var(--ink-5);
  border-radius: 8px;
  border: 2px solid var(--surface-2);
}
::-webkit-scrollbar-thumb:hover { background: var(--ink-4); }
</style>
