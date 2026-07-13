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
    <div>
      <div class="c-{{PREFIX}}-run-card__title">{{ r.title }}</div>
      <div class="c-{{PREFIX}}-run-card__meta">{{ r.courseTag }} · {{ r.dateLabel }} · {{ r.durationLabel }}</div>
    </div>
    <div class="c-{{PREFIX}}-pace-mini">{{ r.avgWpm }}</div>
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
  </article>
</section>
