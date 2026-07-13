<template>
  <Teleport to="body">
    <div
      v-if="open"
      :class="`c-${prefix}-media-sheet`"
      role="dialog"
      aria-modal="true"
      :aria-label="title"
      @click.self="emit('cancel')"
    >
      <div :class="`c-${prefix}-media-sheet__panel`">
        <p :class="`c-${prefix}-media-sheet__title`">{{ title }}</p>
        <p v-if="subtitle" :class="`c-${prefix}-media-sheet__sub`">{{ subtitle }}</p>
        <button
          type="button"
          :class="`c-${prefix}-media-sheet__action`"
          @click="emit('pick', 'camera')"
        >
          <svg :class="`c-${prefix}-mark`" viewBox="0 0 24 24" aria-hidden="true">
            <use :href="`#${prefix}-mark-camera`" />
          </svg>
          Take Photo
        </button>
        <button
          type="button"
          :class="`c-${prefix}-media-sheet__action`"
          @click="emit('pick', 'gallery')"
        >
          <svg :class="`c-${prefix}-mark`" viewBox="0 0 24 24" aria-hidden="true">
            <use :href="`#${prefix}-mark-image`" />
          </svg>
          Choose from Library
        </button>
        <button type="button" :class="`c-${prefix}-media-sheet__cancel`" @click="emit('cancel')">
          Cancel
        </button>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import type { ImageSource } from '../lib/pickImage';

const prefix = '{{PREFIX}}';

withDefaults(
  defineProps<{
    open: boolean;
    title?: string;
    subtitle?: string;
  }>(),
  {
    title: 'Add reference photo',
    subtitle: 'Attach one slide or photo for this section.',
  },
);

const emit = defineEmits<{
  pick: [source: ImageSource];
  cancel: [];
}>();
</script>
