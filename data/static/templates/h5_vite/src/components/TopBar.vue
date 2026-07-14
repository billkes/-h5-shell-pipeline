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
      <svg
        class="c-{{PREFIX}}-topbar__back-icon"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path
          d="M14 7L9 12l5 5"
          fill="none"
          stroke="currentColor"
          stroke-width="2.75"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
      </svg>
      <span class="c-{{PREFIX}}-topbar__back-label">Back</span>
    </button>
    <span
      v-else
      class="c-{{PREFIX}}-topbar__spacer"
      aria-hidden="true"
    />
    <span class="c-{{PREFIX}}-topbar__title">{{ title }}</span>
    <span
      class="c-{{PREFIX}}-topbar__spacer"
      aria-hidden="true"
    />
  </header>
</template>
