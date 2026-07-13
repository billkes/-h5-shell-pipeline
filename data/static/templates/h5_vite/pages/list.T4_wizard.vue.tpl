<!-- SCAFFOLD:pipeline:start — sync_h5_page_scaffold; do not hand-edit template -->
<template>
  <div>
    <TopBar title="{{LIST_TITLE}}" />
    <div class="page-shell">
      <section class="c-{{PREFIX}}-list-hero" data-{{PREFIX}}-landmark="list-hero">
        <p class="c-{{PREFIX}}-list-hero__eyebrow">{{LIST_EYEBROW}}</p>
        <h1 class="c-{{PREFIX}}-list-hero__title">{{LIST_HEADLINE}}</h1>
        <p class="c-{{PREFIX}}-list-hero__sub">{{LIST_SUB}}</p>
      </section>

      <section class="c-{{PREFIX}}-kpi-strip" data-{{PREFIX}}-landmark="list-kpi-strip">
        <div class="c-{{PREFIX}}-kpi-card">
          <div class="c-{{PREFIX}}-kpi-card__val">{{ totalRuns }}</div>
          <div class="c-{{PREFIX}}-kpi-card__label">Total Runs</div>
        </div>
        <div class="c-{{PREFIX}}-kpi-card">
          <div class="c-{{PREFIX}}-kpi-card__val">{{ weekRuns }}</div>
          <div class="c-{{PREFIX}}-kpi-card__label">This Week</div>
        </div>
        <div class="c-{{PREFIX}}-kpi-card">
          <div class="c-{{PREFIX}}-kpi-card__val c-{{PREFIX}}-kpi-card__val--ok">{{ avgWpmKpi }}</div>
          <div class="c-{{PREFIX}}-kpi-card__label">Avg WPM</div>
        </div>
      </section>

      <nav class="c-{{PREFIX}}-chip-rail" data-{{PREFIX}}-landmark="filter-chips">
        <button
          v-for="c in courseChips"
          :key="c"
          type="button"
          class="c-{{PREFIX}}-tag"
          :class="{ 'c-{{PREFIX}}-tag--active': filterCourse === c }"
          @click="toggleCourse(c)"
        >{{ c || 'All' }}</button>
      </nav>

      <div class="c-{{PREFIX}}-list-toolbar" data-{{PREFIX}}-landmark="list-toolbar">
        <span class="c-{{PREFIX}}-list-toolbar__sort">Sort: <strong>{{ sortLabel }}</strong></span>
        <span class="c-{{PREFIX}}-list-toolbar__range">{{ dateRangeLabel }}</span>
      </div>

      <div v-if="!rows.length" class="c-{{PREFIX}}-list-empty" data-{{PREFIX}}-landmark="empty-state">
        <div class="c-{{PREFIX}}-list-empty__icon" aria-hidden="true">◎</div>
        <div class="c-{{PREFIX}}-list-empty__title">No completed runs yet</div>
        <p class="c-{{PREFIX}}-list-empty__sub">Finish a live teleprompter session — runs appear here filtered by course and date.</p>
        <button class="c-{{PREFIX}}-action" type="button" @click="goToHub">Go to Prepare</button>
      </div>

      <section v-else data-{{PREFIX}}-landmark="list-rows">
        <div class="c-{{PREFIX}}-section-head">
          <h2 class="c-{{PREFIX}}-section-head__title">Recent Sessions</h2>
          <span class="c-{{PREFIX}}-section-head__meta">{{ visibleCount }} shown</span>
        </div>
        <article
          v-for="r in rows"
          :key="r.id"
          class="c-{{PREFIX}}-run-card"
          @click="openRun(r.id)"
        >
          <div class="c-{{PREFIX}}-run-card__top">
            <div class="c-{{PREFIX}}-run-card__copy">
              <div class="c-{{PREFIX}}-run-card__title">{{ r.title }}</div>
              <div class="c-{{PREFIX}}-run-card__meta">{{ r.courseTag }} · {{ r.dateLabel }} · {{ r.durationLabel }}</div>
            </div>
            <div class="c-{{PREFIX}}-pace-mini" aria-label="Average pace">
              <span class="c-{{PREFIX}}-pace-mini__num">{{ r.wpm }}</span>
              <span class="c-{{PREFIX}}-pace-mini__unit">WPM</span>
            </div>
          </div>
          <div class="c-{{PREFIX}}-run-card__bottom">
            <div class="c-{{PREFIX}}-run-card__stats">
              <span
                v-if="r.overtimeCount"
                class="c-{{PREFIX}}-stat-pill c-{{PREFIX}}-stat-pill--warn"
              >{{ r.overtimeCount }} OT</span>
              <span v-else class="c-{{PREFIX}}-stat-pill c-{{PREFIX}}-stat-pill--ok">On pace</span>
              <span class="c-{{PREFIX}}-stat-pill">{{ r.sectionCount }} sections</span>
              <span v-if="r.hasNotes" class="c-{{PREFIX}}-stat-pill">Notes saved</span>
            </div>
            <svg class="c-{{PREFIX}}-mark c-{{PREFIX}}-run-card__chevron" viewBox="0 0 24 24"><use href="#{{PREFIX}}-mark-chevron-right" /></svg>
          </div>
        </article>
      </section>
    </div>
    <TabBar />
  </div>
</template>
<!-- SCAFFOLD:pipeline:end -->

<script setup lang="ts">
import TopBar from '../components/TopBar.vue';
import TabBar from '../components/TabBar.vue';
import { useRunsLogic } from './{{VIEW_STEM}}.logic';

const {
  rows,
  courseChips,
  filterCourse,
  toggleCourse,
  openRun,
  goToHub,
  totalRuns,
  weekRuns,
  avgWpmKpi,
  sortLabel,
  dateRangeLabel,
  visibleCount,
} = useRunsLogic();
</script>
