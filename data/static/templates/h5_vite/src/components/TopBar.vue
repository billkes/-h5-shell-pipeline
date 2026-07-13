<script setup lang="ts">
defineProps<{ title: string; back?: boolean }>();
const emit = defineEmits<{ back: [] }>();
</script>

<template>
  <header class="c-{{PREFIX}}-topbar">
    <button
      v-if="back"
      type="button"
      class="c-{{PREFIX}}-topbar__back"
      aria-label="Back"
      @click="emit('back')"
    >
      <svg class="c-{{PREFIX}}-topbar__back-icon" viewBox="0 0 24 24" aria-hidden="true">
        <path
          d="M15 6l-6 6 6 6"
          fill="none"
          stroke="currentColor"
          stroke-width="2.25"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
      </svg>
    </button>
    <span v-else aria-hidden="true" />
    <span class="c-{{PREFIX}}-topbar__title">{{ title }}</span>
    <span aria-hidden="true" />
  </header>
</template>
