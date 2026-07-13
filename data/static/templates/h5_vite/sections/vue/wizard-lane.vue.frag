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
