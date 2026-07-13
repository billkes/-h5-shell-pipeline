<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router';

const route = useRoute();
const router = useRouter();

const tabs = [
  { path: '/hub', label: 'Home' },
  { path: '/settings', label: 'Settings' },
];

function go(path: string) {
  router.push(path);
}
</script>

<template>
  <nav class="c-{{PREFIX}}-tabbar">
    <a
      v-for="t in tabs"
      :key="t.path"
      href="#"
      class="c-{{PREFIX}}-tabbar__item"
      :class="{ 'c-{{PREFIX}}-tabbar__item--active': route.path.startsWith(t.path) }"
      @click.prevent="go(t.path)"
    >
      <span>{{ t.label }}</span>
    </a>
  </nav>
</template>
