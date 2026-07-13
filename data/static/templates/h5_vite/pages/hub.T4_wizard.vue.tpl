<!-- SCAFFOLD:pipeline:start — sync_h5_page_scaffold; do not hand-edit template -->
<template>
  <div>
    <TopBar title="{{HUB_TITLE}}" />
    <div class="page-shell">
      <section class="c-{{PREFIX}}-hub-hero" data-{{PREFIX}}-landmark="hero">
        <p class="c-{{PREFIX}}-hub-hero__eyebrow">{{HERO_EYEBROW}}</p>
        <h1 class="c-{{PREFIX}}-hub-hero__title">{{HERO_TITLE}}</h1>
        <p class="c-{{PREFIX}}-hub-hero__sub">{{HERO_SUB}}</p>
      </section>

      <section class="c-{{PREFIX}}-kpi-strip" data-{{PREFIX}}-landmark="kpi-strip">
        <div class="c-{{PREFIX}}-kpi-card">
          <div class="c-{{PREFIX}}-kpi-card__val">{{ draftCount }}</div>
          <div class="c-{{PREFIX}}-kpi-card__label">Drafts</div>
        </div>
        <div class="c-{{PREFIX}}-kpi-card">
          <div class="c-{{PREFIX}}-kpi-card__val">{{ lastRunLabel }}</div>
          <div class="c-{{PREFIX}}-kpi-card__label">Last Run</div>
        </div>
        <div class="c-{{PREFIX}}-kpi-card">
          <div class="c-{{PREFIX}}-kpi-card__val c-{{PREFIX}}-kpi-card__val--ok">{{ avgWpmLabel }}</div>
          <div class="c-{{PREFIX}}-kpi-card__label">Avg WPM</div>
        </div>
      </section>

      <section class="c-{{PREFIX}}-wizard-lane" data-{{PREFIX}}-landmark="wizard-lane">
        <div class="c-{{PREFIX}}-wizard-lane__label">
          <span>Rehearsal pipeline</span>
          <span>{{ wizardStepLabel }}</span>
        </div>
        <div class="c-{{PREFIX}}-wizard-lane__track">
          <div
            v-for="s in wizardSteps"
            :key="s.n"
            class="c-{{PREFIX}}-wizard-lane__step"
            :class="{
              'c-{{PREFIX}}-wizard-lane__step--done': s.n < wizardStep,
              'c-{{PREFIX}}-wizard-lane__step--current': s.n === wizardStep,
            }"
          >
            <span class="c-{{PREFIX}}-wizard-lane__step-num">{{ s.n }}</span> {{ s.label }}
          </div>
        </div>
      </section>

      <nav class="c-{{PREFIX}}-chip-rail" data-{{PREFIX}}-landmark="chip-rail">
        <button
          v-for="c in courseChips"
          :key="c"
          type="button"
          class="c-{{PREFIX}}-tag"
          :class="{ 'c-{{PREFIX}}-tag--active': activeChip === c }"
          @click="setChip(c)"
        >{{ c }}</button>
      </nav>

      <section class="c-{{PREFIX}}-bento" data-{{PREFIX}}-landmark="feature-bento">
        <article class="c-{{PREFIX}}-bento-tile">
          <div class="c-{{PREFIX}}-bento-tile__icon">
            <svg class="c-{{PREFIX}}-mark" viewBox="0 0 24 24"><use href="#{{PREFIX}}-mark-calendar" /></svg>
          </div>
          <h3 class="c-{{PREFIX}}-bento-tile__title">Time Map</h3>
          <p class="c-{{PREFIX}}-bento-tile__desc">Assign target duration per section before live rehearsal.</p>
        </article>
        <article class="c-{{PREFIX}}-bento-tile">
          <div class="c-{{PREFIX}}-bento-tile__icon c-{{PREFIX}}-bento-tile__icon--green">
            <svg class="c-{{PREFIX}}-mark" viewBox="0 0 24 24"><use href="#{{PREFIX}}-mark-export" /></svg>
          </div>
          <h3 class="c-{{PREFIX}}-bento-tile__title">Live Pace</h3>
          <p class="c-{{PREFIX}}-bento-tile__desc">Real-time WPM gauge during teleprompter.</p>
          <div class="c-{{PREFIX}}-pace-gauge">
            <div class="c-{{PREFIX}}-pace-gauge__bar"><div class="c-{{PREFIX}}-pace-gauge__fill" :style="{ width: paceFill }" /></div>
            <span style="font-size:11px;font-weight:700;color:var(--{{PREFIX}}-accent)">{{ avgWpmLabel }}</span>
          </div>
        </article>
        <article class="c-{{PREFIX}}-bento-tile c-{{PREFIX}}-bento__wide">
          <div class="c-{{PREFIX}}-bento-tile__icon c-{{PREFIX}}-bento-tile__icon--warn">
            <svg class="c-{{PREFIX}}-mark" viewBox="0 0 24 24"><use href="#{{PREFIX}}-mark-warning-circle" /></svg>
          </div>
          <h3 class="c-{{PREFIX}}-bento-tile__title">Structural Overtime</h3>
          <p class="c-{{PREFIX}}-bento-tile__desc">Sections that exceed target are auto-marked before class.</p>
          <div class="c-{{PREFIX}}-waveform" aria-hidden="true">
            <div v-for="i in 7" :key="i" class="c-{{PREFIX}}-waveform__bar" />
          </div>
        </article>
      </section>

      <div class="c-{{PREFIX}}-cta-stack">
        <button class="c-{{PREFIX}}-action" type="button" data-{{PREFIX}}-landmark="cta-primary" @click="startWizard">
          <svg class="c-{{PREFIX}}-mark" viewBox="0 0 24 24"><use href="#{{PREFIX}}-mark-add" /></svg>
          New Rehearsal Plan
        </button>
        <button class="c-{{PREFIX}}-action c-{{PREFIX}}-action--secondary" type="button" @click="importDemo">
          Import Demo Script
        </button>
      </div>

      <section>
        <div class="c-{{PREFIX}}-section-head">
          <h2 class="c-{{PREFIX}}-section-head__title">Your Drafts</h2>
        </div>
        <div v-if="!drafts.length" class="c-{{PREFIX}}-tile" data-{{PREFIX}}-landmark="empty-state" style="text-align:center;color:var(--{{PREFIX}}-on-muted)">
          No drafts yet — start your first rehearsal plan
        </div>
        <div v-else data-{{PREFIX}}-landmark="draft-list">
          <article
            v-for="d in drafts"
            :key="d.id"
            class="c-{{PREFIX}}-draft-card"
            @click="openDraft(d.id)"
          >
            <div style="display:flex;justify-content:space-between;gap:8px">
              <div>
                <div class="c-{{PREFIX}}-draft-card__title">{{ d.title }}</div>
                <div class="c-{{PREFIX}}-draft-card__meta">{{ d.courseTag }} · {{ d.sections.length }} sections</div>
              </div>
              <span class="c-{{PREFIX}}-draft-card__badge" :class="{ 'c-{{PREFIX}}-draft-card__badge--ready': d.mapped }">{{ d.badge }}</span>
            </div>
            <div class="c-{{PREFIX}}-draft-card__progress">
              <div
                v-for="(seg, idx) in d.progress"
                :key="idx"
                class="c-{{PREFIX}}-draft-card__seg"
                :class="{
                  'c-{{PREFIX}}-draft-card__seg--filled': seg === 'filled',
                  'c-{{PREFIX}}-draft-card__seg--done': seg === 'done',
                }"
              />
            </div>
          </article>
        </div>
      </section>
    </div>
    <TabBar />
  </div>
</template>
<!-- SCAFFOLD:pipeline:end -->

<script setup lang="ts">
import TopBar from '../components/TopBar.vue';
import TabBar from '../components/TabBar.vue';
import { useHubLogic } from './{{VIEW_STEM}}.logic';

const {
  drafts,
  draftCount,
  lastRunLabel,
  avgWpmLabel,
  paceFill,
  courseChips,
  activeChip,
  setChip,
  wizardStep,
  wizardStepLabel,
  wizardSteps,
  startWizard,
  importDemo,
  openDraft,
} = useHubLogic();
</script>
