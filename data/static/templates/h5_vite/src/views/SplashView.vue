<template>
  <div class="page">
    <div class="mark">{{APP_NAME}}</div>
    <p class="muted">Splash — replace in Build Agent Part 3</p>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { bridgeCall } from '../bridge';

const router = useRouter();

onMounted(() => {
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      bridgeCall('shellReady', {});
      setTimeout(() => router.replace('/welcome'), 800);
    });
  });
});
</script>

<style scoped>
.page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 24px;
}
.mark {
  font-size: 28px;
  font-weight: 700;
  color: var(--{{PREFIX}}-primary);
}
.muted {
  color: var(--{{PREFIX}}-on-muted);
  font-size: 14px;
}
</style>
