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
      <span class="c-{{PREFIX}}-pace-gauge__label">{{ avgWpmLabel }}</span>
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
