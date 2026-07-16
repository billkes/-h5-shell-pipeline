<div class="settings-block">
<p class="c-{{PREFIX}}-settings-group-label">Wallet</p>
<nav class="c-{{PREFIX}}-settings-menu" data-{{PREFIX}}-landmark="settings-menu">
  <button class="c-{{PREFIX}}-settings-row" type="button" @click="openStore">
    <span class="c-{{PREFIX}}-settings-row__lead">
      <span class="c-{{PREFIX}}-settings-row__icon c-{{PREFIX}}-settings-row__icon--primary">
        <svg class="c-{{PREFIX}}-mark" viewBox="0 0 24 24"><use href="#{{PREFIX}}-mark-store" /></svg>
      </span>
      <span class="c-{{PREFIX}}-settings-row__text">Coin Store</span>
    </span>
    <svg class="c-{{PREFIX}}-mark c-{{PREFIX}}-settings-row__chevron" viewBox="0 0 24 24"><use href="#{{PREFIX}}-mark-chevron-right" /></svg>
  </button>
</nav>

<p class="c-{{PREFIX}}-settings-group-label">Legal</p>
<nav class="c-{{PREFIX}}-settings-menu">
  <button class="c-{{PREFIX}}-settings-row" type="button" @click="openLegal('privacy')">
    <span class="c-{{PREFIX}}-settings-row__lead">
      <span class="c-{{PREFIX}}-settings-row__icon">
        <svg class="c-{{PREFIX}}-mark" viewBox="0 0 24 24"><use href="#{{PREFIX}}-mark-list" /></svg>
      </span>
      <span class="c-{{PREFIX}}-settings-row__text">Privacy Agreement</span>
    </span>
    <svg class="c-{{PREFIX}}-mark c-{{PREFIX}}-settings-row__chevron" viewBox="0 0 24 24"><use href="#{{PREFIX}}-mark-chevron-right" /></svg>
  </button>
  <button class="c-{{PREFIX}}-settings-row" type="button" @click="openLegal('terms')">
    <span class="c-{{PREFIX}}-settings-row__lead">
      <span class="c-{{PREFIX}}-settings-row__icon">
        <svg class="c-{{PREFIX}}-mark" viewBox="0 0 24 24"><use href="#{{PREFIX}}-mark-list" /></svg>
      </span>
      <span class="c-{{PREFIX}}-settings-row__text">User Agreement</span>
    </span>
    <svg class="c-{{PREFIX}}-mark c-{{PREFIX}}-settings-row__chevron" viewBox="0 0 24 24"><use href="#{{PREFIX}}-mark-chevron-right" /></svg>
  </button>
</nav>

<p class="c-{{PREFIX}}-settings-group-label">Data</p>
<nav class="c-{{PREFIX}}-settings-menu c-{{PREFIX}}-settings-menu--tail">
  <button class="c-{{PREFIX}}-settings-row c-{{PREFIX}}-settings-row--danger" type="button" @click="showClear = true">
    <span class="c-{{PREFIX}}-settings-row__lead">
      <span class="c-{{PREFIX}}-settings-row__icon c-{{PREFIX}}-settings-row__icon--danger">
        <svg class="c-{{PREFIX}}-mark" viewBox="0 0 24 24"><use href="#{{PREFIX}}-mark-delete" /></svg>
      </span>
      <span class="c-{{PREFIX}}-settings-row__text">Clear rehearsal data</span>
    </span>
    <svg class="c-{{PREFIX}}-mark c-{{PREFIX}}-settings-row__chevron" viewBox="0 0 24 24"><use href="#{{PREFIX}}-mark-chevron-right" /></svg>
  </button>
  <!-- H5_PLAZA_DEV_ENTRANCE_START -->
  <button class="c-{{PREFIX}}-settings-dev" type="button" @click="openPlaza">Dev: Bridge Plaza</button>
  <!-- H5_PLAZA_DEV_ENTRANCE_END -->
</nav>
</div>
