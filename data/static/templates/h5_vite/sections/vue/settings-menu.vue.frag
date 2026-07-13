<nav class="c-{{PREFIX}}-settings-menu" data-{{PREFIX}}-landmark="settings-menu">
  <button class="c-{{PREFIX}}-settings-row" type="button" @click="openStore">
    <span>Coin Store</span>
    <svg class="c-{{PREFIX}}-mark" viewBox="0 0 24 24"><use href="#{{PREFIX}}-mark-chevron-right" /></svg>
  </button>
  <button class="c-{{PREFIX}}-settings-row" type="button" @click="openLegal('privacy')">
    <span>Privacy Agreement</span>
    <svg class="c-{{PREFIX}}-mark" viewBox="0 0 24 24"><use href="#{{PREFIX}}-mark-chevron-right" /></svg>
  </button>
  <button class="c-{{PREFIX}}-settings-row" type="button" @click="openLegal('terms')">
    <span>User Agreement</span>
    <svg class="c-{{PREFIX}}-mark" viewBox="0 0 24 24"><use href="#{{PREFIX}}-mark-chevron-right" /></svg>
  </button>
  <button class="c-{{PREFIX}}-settings-row c-{{PREFIX}}-settings-row--danger" type="button" @click="showClear = true">
    <span>Clear Rehearsal Data</span>
    <svg class="c-{{PREFIX}}-mark" viewBox="0 0 24 24"><use href="#{{PREFIX}}-mark-chevron-right" /></svg>
  </button>
  <!-- H5_PLAZA_DEV_ENTRANCE_START -->
  <button class="c-{{PREFIX}}-action c-{{PREFIX}}-action--secondary" type="button" style="width:100%;margin-top:16px" @click="openPlaza">Dev: Bridge Plaza</button>
  <!-- H5_PLAZA_DEV_ENTRANCE_END -->
</nav>
