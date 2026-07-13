.c-{{PREFIX}}-section-head {
  display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;
}
.c-{{PREFIX}}-section-head__title {
  font-family: var(--{{PREFIX}}-font-display, inherit);
  font-size: 14px; font-weight: 700;
}
.c-{{PREFIX}}-section-head__meta { font-size: 12px; color: var(--{{PREFIX}}-on-muted); }
.c-{{PREFIX}}-draft-card {
  background: var(--{{PREFIX}}-card);
  border: 1px solid var(--{{PREFIX}}-border);
  border-radius: var(--{{PREFIX}}-radius-lg, 16px);
  padding: 16px; margin-bottom: 8px; cursor: pointer;
}
.c-{{PREFIX}}-draft-card__title { font-weight: 700; font-size: 14px; margin-bottom: 4px; }
.c-{{PREFIX}}-draft-card__meta { font-size: 12px; color: var(--{{PREFIX}}-on-muted); }
.c-{{PREFIX}}-draft-card__badge {
  font-size: 12px; font-weight: 700; padding: 4px 8px; border-radius: 999px;
  background: rgba(234, 88, 12, 0.18); color: var(--{{PREFIX}}-secondary);
}
.c-{{PREFIX}}-draft-card__badge--ready {
  background: rgba(5, 150, 105, 0.18); color: var(--{{PREFIX}}-accent);
}
.c-{{PREFIX}}-draft-card__progress { margin-top: 8px; display: flex; gap: 4px; }
.c-{{PREFIX}}-draft-card__seg {
  flex: 1; height: 3px; border-radius: 2px; background: var(--{{PREFIX}}-muted);
}
.c-{{PREFIX}}-draft-card__seg--filled { background: var(--{{PREFIX}}-primary); }
.c-{{PREFIX}}-draft-card__seg--done { background: var(--{{PREFIX}}-accent); }
