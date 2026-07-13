<script setup lang="ts">
import { computed } from 'vue';
import { LEGAL } from '../legal/{{PREFIX}}_legal_bundled';
import { formatLegalBody } from '../lib/formatLegalBody';

const props = defineProps<{ doc: 'privacy' | 'terms' }>();
const emit = defineEmits<{ close: [] }>();

const prefix = '{{PREFIX}}';
const rawBody = computed(() => (props.doc === 'privacy' ? LEGAL.privacy : LEGAL.terms));
const formatted = computed(() => formatLegalBody(rawBody.value, prefix));
const title = computed(
  () =>
    formatted.value.title ||
    (props.doc === 'terms' ? 'User Agreement' : 'Privacy Agreement'),
);
</script>

<template>
  <div class="c-{{PREFIX}}-legal-veil" @click.self="emit('close')">
    <div class="c-{{PREFIX}}-legal-card">
      <header class="c-{{PREFIX}}-legal-header">
        <h1 class="c-{{PREFIX}}-legal-title">{{ title }}</h1>
        <button
          type="button"
          class="c-{{PREFIX}}-legal-close"
          aria-label="Close"
          @click="emit('close')"
        >
          <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
            <path
              d="M18 6L6 18M6 6l12 12"
              fill="none"
              stroke="currentColor"
              stroke-width="2.25"
              stroke-linecap="round"
            />
          </svg>
        </button>
      </header>
      <div class="c-{{PREFIX}}-legal-scroll" v-html="formatted.bodyHtml" />
    </div>
  </div>
</template>
