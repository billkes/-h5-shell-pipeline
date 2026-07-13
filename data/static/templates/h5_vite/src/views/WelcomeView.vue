<template>
  <div class="page">
    <h1>Welcome</h1>
    <p class="muted">18+ gate — implement per 功能文档.md</p>
    <label class="row">
      <input v-model="checked" type="checkbox" />
      <span>I am 18 or older</span>
    </label>
    <button class="cta" type="button" :disabled="!checked" @click="go">Continue</button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';

const checked = ref(false);

function go(): void {
  localStorage.setItem('{{PREFIX}}_welcome_v1', 'true');
  location.hash = '#/rehearse';
}
</script>

<style scoped>
.page {
  min-height: 100vh;
  padding: calc(24px + var(--safe-top)) 24px 24px;
}
.muted {
  color: var(--{{PREFIX}}-on-muted);
}
.row {
  display: flex;
  gap: 8px;
  align-items: center;
  margin: 24px 0;
}
.cta {
  width: 100%;
  min-height: 44px;
  border: 0;
  border-radius: 12px;
  background: var(--{{PREFIX}}-primary);
  color: #fff;
  font-weight: 600;
}
.cta:disabled {
  opacity: 0.45;
}
</style>
