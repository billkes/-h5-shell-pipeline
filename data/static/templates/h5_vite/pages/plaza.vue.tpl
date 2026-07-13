<template>
  <div class="c-{{PREFIX}}-plaza">
    <TopBar title="Bridge Plaza" back @back="goBack" />

    <div class="page-stack c-{{PREFIX}}-plaza__body">
      <section class="c-{{PREFIX}}-plaza-hero" data-{{PREFIX}}-landmark="plaza-hero">
        <p class="c-{{PREFIX}}-plaza-hero__eyebrow">Developer QA</p>
        <h1 class="c-{{PREFIX}}-plaza-hero__title">Bridge capability matrix</h1>
        <p class="c-{{PREFIX}}-plaza-hero__sub">
          Tap each action to verify native Bridge responses. IAP uses sandbox SKU
          {{ PLAZA_TEST_PURCHASE_PRODUCT_ID }}.
        </p>
      </section>

      <article
        v-if="lastResult"
        class="c-{{PREFIX}}-plaza-result"
        :class="`c-{{PREFIX}}-plaza-result--${lastResult.state}`"
        role="status"
        aria-live="polite"
      >
        <span class="c-{{PREFIX}}-plaza-result__badge">{{ resultBadge }}</span>
        <div class="c-{{PREFIX}}-plaza-result__text">
          <p class="c-{{PREFIX}}-plaza-result__title">{{ lastResult.title }}</p>
          <p class="c-{{PREFIX}}-plaza-result__detail">{{ lastResult.detail }}</p>
          <p class="c-{{PREFIX}}-plaza-result__action">{{ lastResult.action }}</p>
        </div>
      </article>

      <section
        v-for="group in groupedActions"
        :key="group.id"
        class="c-{{PREFIX}}-plaza-group"
        :data-{{PREFIX}}-landmark="`plaza-${group.id}`"
      >
        <header class="c-{{PREFIX}}-plaza-group__head">
          <h2 class="c-{{PREFIX}}-plaza-group__title">{{ group.label }}</h2>
        </header>
        <div class="c-{{PREFIX}}-plaza-grid">
          <button
            v-for="action in group.actions"
            :key="action.id"
            type="button"
            class="c-{{PREFIX}}-plaza-action"
            :class="`c-{{PREFIX}}-plaza-action--${action.state}`"
            :disabled="busy"
            @click="call(action.id)"
          >
            <span class="c-{{PREFIX}}-plaza-action__top">
              <span class="c-{{PREFIX}}-plaza-action__label">{{ action.label }}</span>
              <span class="c-{{PREFIX}}-plaza-action__state">{{ stateLabel(action.state) }}</span>
            </span>
            <span class="c-{{PREFIX}}-plaza-action__hint">{{ action.hint }}</span>
            <span v-if="action.state === 'calling'" class="c-{{PREFIX}}-plaza-action__spinner" aria-hidden="true" />
          </button>
        </div>
      </section>

      <section class="c-{{PREFIX}}-plaza-log-wrap" data-{{PREFIX}}-landmark="plaza-log">
        <header class="c-{{PREFIX}}-section-head">
          <h2 class="c-{{PREFIX}}-section-head__title">Raw response</h2>
          <span class="c-{{PREFIX}}-section-head__meta">{{ log ? 'latest' : 'empty' }}</span>
        </header>
        <pre class="c-{{PREFIX}}-plaza-log">{{ log || 'Run an action to see Bridge payload here.' }}</pre>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import TopBar from '../components/TopBar.vue';
import {
  PLAZA_TEST_PURCHASE_PRODUCT_ID,
  type PlazaActionState,
  usePlazaLogic,
} from './PlazaView.logic';

const { groupedActions, lastResult, log, busy, call, goBack } = usePlazaLogic();

const resultBadge = computed(() => {
  if (!lastResult.value) return '';
  const map: Record<PlazaActionState, string> = {
    idle: '',
    calling: '…',
    success: 'OK',
    error: 'ERR',
    cancelled: '—',
  };
  return map[lastResult.value.state];
});

function stateLabel(state: PlazaActionState): string {
  if (state === 'calling') return 'Running';
  if (state === 'success') return 'OK';
  if (state === 'error') return 'Failed';
  if (state === 'cancelled') return 'Cancelled';
  return 'Ready';
}
</script>

<style scoped>
.c-{{PREFIX}}-plaza__body {
  padding-bottom: calc(24px + var(--safe-bottom));
}

.c-{{PREFIX}}-plaza-hero {
  margin-bottom: var(--space-lg, 24px);
}

.c-{{PREFIX}}-plaza-hero__eyebrow {
  font-size: 12px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--{{PREFIX}}-secondary);
  margin: 0 0 8px;
}

.c-{{PREFIX}}-plaza-hero__title {
  margin: 0 0 8px;
  font-family: var(--{{PREFIX}}-font-display, inherit);
  font-size: 22px;
  font-weight: 700;
  line-height: 1.2;
}

.c-{{PREFIX}}-plaza-hero__sub {
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
  color: var(--{{PREFIX}}-on-muted);
}

.c-{{PREFIX}}-plaza-result {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: var(--space-lg, 24px);
  padding: 14px 16px;
  border-radius: var(--{{PREFIX}}-radius-lg, 16px);
  border: 1px solid var(--{{PREFIX}}-border);
  background: var(--{{PREFIX}}-card);
}

.c-{{PREFIX}}-plaza-result--success {
  border-color: color-mix(in srgb, var(--{{PREFIX}}-accent) 45%, var(--{{PREFIX}}-border));
  background: color-mix(in srgb, var(--{{PREFIX}}-accent) 10%, var(--{{PREFIX}}-card));
}

.c-{{PREFIX}}-plaza-result--error {
  border-color: color-mix(in srgb, var(--{{PREFIX}}-destructive) 45%, var(--{{PREFIX}}-border));
  background: color-mix(in srgb, var(--{{PREFIX}}-destructive) 8%, var(--{{PREFIX}}-card));
}

.c-{{PREFIX}}-plaza-result--cancelled {
  border-color: color-mix(in srgb, var(--{{PREFIX}}-secondary) 35%, var(--{{PREFIX}}-border));
  background: color-mix(in srgb, var(--{{PREFIX}}-secondary) 8%, var(--{{PREFIX}}-card));
}

.c-{{PREFIX}}-plaza-result__badge {
  flex-shrink: 0;
  min-width: 40px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  background: var(--{{PREFIX}}-muted);
  color: var(--{{PREFIX}}-fg);
}

.c-{{PREFIX}}-plaza-result--success .c-{{PREFIX}}-plaza-result__badge {
  background: var(--{{PREFIX}}-accent);
  color: #fff;
}

.c-{{PREFIX}}-plaza-result--error .c-{{PREFIX}}-plaza-result__badge {
  background: var(--{{PREFIX}}-destructive);
  color: #fff;
}

.c-{{PREFIX}}-plaza-result__title {
  margin: 0 0 4px;
  font-weight: 700;
  font-size: 14px;
}

.c-{{PREFIX}}-plaza-result__detail {
  margin: 0;
  font-size: 12px;
  line-height: 1.45;
  color: var(--{{PREFIX}}-on-muted);
}

.c-{{PREFIX}}-plaza-result__action {
  margin: 6px 0 0;
  font-size: 11px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--{{PREFIX}}-secondary);
}

.c-{{PREFIX}}-plaza-group {
  margin-bottom: var(--space-lg, 24px);
}

.c-{{PREFIX}}-plaza-group__title {
  margin: 0;
  font-family: var(--{{PREFIX}}-font-display, inherit);
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.c-{{PREFIX}}-plaza-grid {
  display: grid;
  gap: 8px;
  margin-top: 10px;
}

.c-{{PREFIX}}-plaza-action {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  width: 100%;
  padding: 14px 16px;
  border: 1px solid var(--{{PREFIX}}-border);
  border-radius: var(--{{PREFIX}}-radius-md, 12px);
  background: var(--{{PREFIX}}-card);
  color: var(--{{PREFIX}}-fg);
  text-align: left;
  cursor: pointer;
  transition: border-color 0.15s ease, transform 0.15s ease;
}

.c-{{PREFIX}}-plaza-action:active:not(:disabled) {
  transform: scale(0.99);
}

.c-{{PREFIX}}-plaza-action:disabled {
  opacity: 0.72;
  cursor: wait;
}

.c-{{PREFIX}}-plaza-action--calling {
  border-color: color-mix(in srgb, var(--{{PREFIX}}-primary) 40%, var(--{{PREFIX}}-border));
}

.c-{{PREFIX}}-plaza-action--success {
  border-color: color-mix(in srgb, var(--{{PREFIX}}-accent) 40%, var(--{{PREFIX}}-border));
}

.c-{{PREFIX}}-plaza-action--error {
  border-color: color-mix(in srgb, var(--{{PREFIX}}-destructive) 40%, var(--{{PREFIX}}-border));
}

.c-{{PREFIX}}-plaza-action--cancelled {
  border-color: color-mix(in srgb, var(--{{PREFIX}}-secondary) 30%, var(--{{PREFIX}}-border));
}

.c-{{PREFIX}}-plaza-action__top {
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.c-{{PREFIX}}-plaza-action__label {
  font-size: 14px;
  font-weight: 700;
}

.c-{{PREFIX}}-plaza-action__state {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--{{PREFIX}}-on-muted);
}

.c-{{PREFIX}}-plaza-action--success .c-{{PREFIX}}-plaza-action__state {
  color: var(--{{PREFIX}}-accent);
}

.c-{{PREFIX}}-plaza-action--error .c-{{PREFIX}}-plaza-action__state {
  color: var(--{{PREFIX}}-destructive);
}

.c-{{PREFIX}}-plaza-action__hint {
  font-size: 12px;
  line-height: 1.4;
  color: var(--{{PREFIX}}-on-muted);
}

.c-{{PREFIX}}-plaza-action__spinner {
  position: absolute;
  right: 14px;
  bottom: 14px;
  width: 16px;
  height: 16px;
  border: 2px solid color-mix(in srgb, var(--{{PREFIX}}-primary) 25%, transparent);
  border-top-color: var(--{{PREFIX}}-primary);
  border-radius: 50%;
  animation: {{PREFIX}}-plaza-spin 0.8s linear infinite;
}

@keyframes {{PREFIX}}-plaza-spin {
  to {
    transform: rotate(360deg);
  }
}

.c-{{PREFIX}}-plaza-log-wrap {
  margin-top: 8px;
}

.c-{{PREFIX}}-plaza-log {
  margin: 0;
  padding: 12px 14px;
  min-height: 88px;
  max-height: 220px;
  overflow: auto;
  border: 1px solid var(--{{PREFIX}}-border);
  border-radius: var(--{{PREFIX}}-radius-md, 12px);
  background: var(--{{PREFIX}}-muted);
  font-size: 11px;
  line-height: 1.45;
  color: var(--{{PREFIX}}-on-muted);
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
