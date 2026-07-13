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
