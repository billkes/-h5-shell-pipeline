<!-- SCAFFOLD:pipeline:start — sync_h5_page_scaffold; do not hand-edit template -->
<template>
  <div>
    <TopBar title="{{LIST_TITLE}}" />
    <div class="page-shell">
      <div class="c-{{PREFIX}}-list-kpi" data-{{PREFIX}}-landmark="filter-chips">
        <button
          v-for="c in courseChips"
          :key="c"
          type="button"
          class="c-{{PREFIX}}-tag"
          :class="{ 'c-{{PREFIX}}-tag--active': filterCourse === c }"
          @click="toggleCourse(c)"
        >{{ c || 'All' }}</button>
      </div>
      <div v-if="!rows.length" class="c-{{PREFIX}}-tile" data-{{PREFIX}}-landmark="empty-state" style="text-align:center;color:var(--{{PREFIX}}-on-muted)">
        No completed runs — finish a live session first
      </div>
      <div v-else data-{{PREFIX}}-landmark="list-rows">
        <div
          v-for="r in rows"
          :key="r.id"
          class="c-{{PREFIX}}-tile c-{{PREFIX}}-list-row"
          @click="openRun(r.id)"
        >
          <div>
            <div style="font-weight:600">{{ r.courseTag }}</div>
            <div style="font-size:12px;color:var(--{{PREFIX}}-on-muted)">{{ formatDate(r.startedAt) }}</div>
          </div>
          <div style="display:flex;align-items:center;gap:8px">
            <span v-if="r.overtimeCount" class="c-{{PREFIX}}-tag c-{{PREFIX}}-tag--warn">{{ r.overtimeCount }} OT</span>
            <svg class="c-{{PREFIX}}-mark" viewBox="0 0 24 24"><use href="#{{PREFIX}}-mark-chevron-right" /></svg>
          </div>
        </div>
      </div>
    </div>
    <TabBar />
  </div>
</template>
<!-- SCAFFOLD:pipeline:end -->

<script setup lang="ts">
import TopBar from '../components/TopBar.vue';
import TabBar from '../components/TabBar.vue';
import { useRunsLogic } from './{{VIEW_STEM}}.logic';

const { rows, courseChips, filterCourse, toggleCourse, formatDate, openRun } = useRunsLogic();
</script>
