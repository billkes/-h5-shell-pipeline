.c-{{PREFIX}}-run-card {
  background: var(--{{PREFIX}}-card);
  border: 1px solid var(--{{PREFIX}}-border);
  border-radius: var(--{{PREFIX}}-radius-lg, 16px);
  padding: 14px 16px; margin-bottom: 10px; cursor: pointer;
  display: grid; grid-template-columns: 1fr auto; gap: 8px 12px; align-items: center;
}
.c-{{PREFIX}}-run-card__title { font-weight: 700; font-size: 14px; margin-bottom: 2px; }
.c-{{PREFIX}}-run-card__meta { font-size: 12px; color: var(--{{PREFIX}}-on-muted); }
.c-{{PREFIX}}-run-card__stats {
  grid-column: 1 / -1; display: flex; gap: 8px; flex-wrap: wrap; align-items: center;
}
.c-{{PREFIX}}-run-card__chevron { color: var(--{{PREFIX}}-on-muted); justify-self: end; }
.c-{{PREFIX}}-stat-pill {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 4px 8px; border-radius: 999px;
  background: var(--{{PREFIX}}-muted); font-size: 12px; font-weight: 600;
}
.c-{{PREFIX}}-stat-pill--ok { color: var(--{{PREFIX}}-accent); background: rgba(5, 150, 105, 0.12); }
.c-{{PREFIX}}-stat-pill--warn { color: var(--{{PREFIX}}-destructive); background: rgba(220, 38, 38, 0.12); }
.c-{{PREFIX}}-pace-mini {
  width: 36px; height: 36px; border-radius: 50%;
  border: 3px solid var(--{{PREFIX}}-muted); border-top-color: var(--{{PREFIX}}-accent);
  display: grid; place-items: center;
  font-size: 12px; font-weight: 700; color: var(--{{PREFIX}}-accent);
}
.c-{{PREFIX}}-list-empty {
  text-align: center; padding: 32px 20px;
  background: var(--{{PREFIX}}-card); border: 1px solid var(--{{PREFIX}}-border);
  border-radius: var(--{{PREFIX}}-radius-lg, 16px); color: var(--{{PREFIX}}-on-muted);
}
.c-{{PREFIX}}-list-empty__icon {
  width: 48px; height: 48px; margin: 0 auto 12px; border-radius: 12px;
  background: rgba(234, 88, 12, 0.12); display: grid; place-items: center;
  color: var(--{{PREFIX}}-primary); font-size: 22px;
}
.c-{{PREFIX}}-list-empty__title { font-weight: 700; color: var(--{{PREFIX}}-fg); margin-bottom: 6px; }
.c-{{PREFIX}}-list-empty__sub { font-size: 13px; line-height: 1.5; margin-bottom: 16px; }
@media (prefers-reduced-motion: reduce) {
  .c-{{PREFIX}}-waveform__bar { animation: none !important; }
}
