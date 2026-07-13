<div v-if="showClear" class="c-{{PREFIX}}-dialog-veil" @click.self="showClear = false">
  <div class="c-{{PREFIX}}-dialog">
    <p>Delete all rehearsals?</p>
    <div style="display:flex;gap:8px;margin-top:16px">
      <button class="c-{{PREFIX}}-action c-{{PREFIX}}-action--secondary" type="button" style="flex:1" @click="showClear = false">Cancel</button>
      <button class="c-{{PREFIX}}-action" type="button" style="flex:1" @click="clearData">Clear</button>
    </div>
  </div>
</div>
