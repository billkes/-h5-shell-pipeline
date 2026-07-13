.c-{{PREFIX}}-settings-wallet {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 22px;
}
.c-{{PREFIX}}-settings-wallet-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  min-height: 108px;
  padding: 14px 12px 12px;
  border: 1px solid var(--{{PREFIX}}-border);
  border-radius: var(--{{PREFIX}}-radius-lg, 16px);
  background:
    radial-gradient(120% 90% at 100% 0%, var(--{{PREFIX}}-ambient-a), transparent 58%),
    var(--{{PREFIX}}-card);
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05);
}
.c-{{PREFIX}}-settings-wallet-card--exports {
  background:
    radial-gradient(120% 90% at 100% 0%, var(--{{PREFIX}}-ambient-c), transparent 58%),
    var(--{{PREFIX}}-card);
}
.c-{{PREFIX}}-settings-wallet-card__icon {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border-radius: 10px;
  background: rgba(234, 88, 12, 0.14);
  color: var(--{{PREFIX}}-primary);
}
.c-{{PREFIX}}-settings-wallet-card--exports .c-{{PREFIX}}-settings-wallet-card__icon {
  background: rgba(5, 150, 105, 0.14);
  color: var(--{{PREFIX}}-accent);
}
.c-{{PREFIX}}-settings-wallet-card__icon .c-{{PREFIX}}-mark {
  width: 18px;
  height: 18px;
}
.c-{{PREFIX}}-settings-wallet-card__val {
  margin: 6px 0 0;
  font-family: var(--{{PREFIX}}-font-display, inherit);
  font-size: 26px;
  font-weight: 700;
  line-height: 1.1;
  color: var(--{{PREFIX}}-primary);
}
.c-{{PREFIX}}-settings-wallet-card__val--ok { color: var(--{{PREFIX}}-accent); }
.c-{{PREFIX}}-settings-wallet-card__label {
  margin: 0;
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--{{PREFIX}}-on-muted);
}
