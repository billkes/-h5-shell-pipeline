.c-{{PREFIX}}-run-card {
  background: var(--{{PREFIX}}-card);
  border: 1px solid var(--{{PREFIX}}-border);
  border-radius: var(--{{PREFIX}}-radius-lg, 16px);
  padding: 14px 16px; margin-bottom: 10px; cursor: pointer;
  display: flex; flex-direction: column; gap: 10px;
  overflow: hidden;
}
.c-{{PREFIX}}-run-card__top {
  display: flex; align-items: flex-start; justify-content: space-between; gap: 12px;
  min-width: 0;
}
.c-{{PREFIX}}-run-card__copy {
  flex: 1; min-width: 0;
}
.c-{{PREFIX}}-run-card__title {
  font-weight: 700; font-size: 14px; margin-bottom: 2px;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  word-break: break-word;
  overflow-wrap: anywhere;
}
.c-{{PREFIX}}-run-card__meta { font-size: 12px; color: var(--{{PREFIX}}-on-muted); }
.c-{{PREFIX}}-run-card__bottom {
  display: flex; align-items: center; justify-content: space-between; gap: 8px;
  min-width: 0;
}
.c-{{PREFIX}}-run-card__stats {
  display: flex; gap: 8px; flex-wrap: wrap; align-items: center;
  flex: 1; min-width: 0;
}
.c-{{PREFIX}}-run-card__chevron {
  flex-shrink: 0; width: 20px; height: 20px; color: var(--{{PREFIX}}-on-muted);
}
.c-{{PREFIX}}-stat-pill {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 4px 8px; border-radius: 999px;
  background: var(--{{PREFIX}}-muted); font-size: 12px; font-weight: 600;
  white-space: nowrap;
}
.c-{{PREFIX}}-stat-pill--ok { color: var(--{{PREFIX}}-accent); background: rgba(5, 150, 105, 0.12); }
.c-{{PREFIX}}-stat-pill--warn { color: var(--{{PREFIX}}-destructive); background: rgba(220, 38, 38, 0.12); }
.c-{{PREFIX}}-pace-mini {
  flex-shrink: 0;
  width: 52px; height: 52px; box-sizing: border-box;
  border-radius: 50%;
  border: 3px solid var(--{{PREFIX}}-muted); border-top-color: var(--{{PREFIX}}-accent);
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  line-height: 1; padding: 2px;
}
.c-{{PREFIX}}-pace-mini__num {
  font-size: 13px; font-weight: 700; color: var(--{{PREFIX}}-accent);
}
.c-{{PREFIX}}-pace-mini__unit {
  font-size: 8px; font-weight: 700; color: var(--{{PREFIX}}-accent);
  letter-spacing: 0.04em; margin-top: 1px;
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
