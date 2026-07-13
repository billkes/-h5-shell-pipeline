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
      <div class="c-{{PREFIX}}-draft-card__head">
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
