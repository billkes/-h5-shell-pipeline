.c-{{PREFIX}}-kpi-strip {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px;
  margin-bottom: var(--space-lg, 24px);
}
.c-{{PREFIX}}-kpi-card {
  background: var(--{{PREFIX}}-card);
  border: 1px solid var(--{{PREFIX}}-border);
  border-radius: var(--{{PREFIX}}-radius-md, 12px);
  padding: 12px 10px; text-align: center;
}
.c-{{PREFIX}}-kpi-card__val {
  font-family: var(--{{PREFIX}}-font-display, inherit);
  font-size: 20px; font-weight: 700; color: var(--{{PREFIX}}-primary); line-height: 1.2;
}
.c-{{PREFIX}}-kpi-card__val--ok { color: var(--{{PREFIX}}-accent); }
.c-{{PREFIX}}-kpi-card__label {
  font-size: 12px; color: var(--{{PREFIX}}-on-muted); margin-top: 4px;
  text-transform: uppercase; letter-spacing: 0.06em;
}
