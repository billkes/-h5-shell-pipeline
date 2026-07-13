<script setup lang="ts">
defineProps<{ title: string; back?: boolean }>();
const emit = defineEmits<{ back: [] }>();
</script>

<template>
  <header class="c-{{PREFIX}}-topbar">
    <button
      v-if="back"
      type="button"
      class="c-{{PREFIX}}-action c-{{PREFIX}}-action--ghost"
      aria-label="Back"
      @click="emit('back')"
    >
      ←
    </button>
    <span v-else aria-hidden="true" />
    <span class="c-{{PREFIX}}-topbar__title">{{ title }}</span>
    <span aria-hidden="true" />
  </header>
</template>
