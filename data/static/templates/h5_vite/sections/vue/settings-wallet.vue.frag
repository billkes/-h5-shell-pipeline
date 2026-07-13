<section class="c-{{PREFIX}}-settings-wallet" data-{{PREFIX}}-landmark="settings-wallet">
  <article class="c-{{PREFIX}}-settings-wallet-card c-{{PREFIX}}-settings-wallet-card--coins">
    <span class="c-{{PREFIX}}-settings-wallet-card__icon" aria-hidden="true">
      <svg class="c-{{PREFIX}}-mark" viewBox="0 0 24 24"><use href="#{{PREFIX}}-mark-store" /></svg>
    </span>
    <p class="c-{{PREFIX}}-settings-wallet-card__val">{{ balance }}</p>
    <p class="c-{{PREFIX}}-settings-wallet-card__label">Coins</p>
  </article>
  <article class="c-{{PREFIX}}-settings-wallet-card c-{{PREFIX}}-settings-wallet-card--exports">
    <span class="c-{{PREFIX}}-settings-wallet-card__icon" aria-hidden="true">
      <svg class="c-{{PREFIX}}-mark" viewBox="0 0 24 24"><use href="#{{PREFIX}}-mark-export" /></svg>
    </span>
    <p class="c-{{PREFIX}}-settings-wallet-card__val c-{{PREFIX}}-settings-wallet-card__val--ok">{{ freeRemaining }}</p>
    <p class="c-{{PREFIX}}-settings-wallet-card__label">Free exports</p>
  </article>
</section>
