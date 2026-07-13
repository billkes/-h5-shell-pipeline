<div v-if="showClear" class="c-{{PREFIX}}-dialog-veil" @click.self="showClear = false">
  <div class="c-{{PREFIX}}-dialog c-{{PREFIX}}-settings-dialog">
    <span class="c-{{PREFIX}}-settings-dialog__icon" aria-hidden="true">
      <svg class="c-{{PREFIX}}-mark" viewBox="0 0 24 24"><use href="#{{PREFIX}}-mark-warning-circle" /></svg>
    </span>
    <h2 class="c-{{PREFIX}}-settings-dialog__title">Clear rehearsal data?</h2>
    <p class="c-{{PREFIX}}-settings-dialog__sub">This removes all saved plans, runs, and exports. It cannot be undone.</p>
    <div class="c-{{PREFIX}}-settings-dialog__actions">
      <button class="c-{{PREFIX}}-action c-{{PREFIX}}-action--secondary" type="button" @click="showClear = false">Cancel</button>
      <button class="c-{{PREFIX}}-action c-{{PREFIX}}-settings-dialog__confirm" type="button" @click="clearData">Clear</button>
    </div>
  </div>
</div>
