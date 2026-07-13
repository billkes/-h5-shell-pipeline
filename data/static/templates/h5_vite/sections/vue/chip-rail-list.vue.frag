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
