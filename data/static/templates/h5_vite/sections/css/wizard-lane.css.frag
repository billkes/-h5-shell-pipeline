.c-{{PREFIX}}-wizard-lane { margin-bottom: var(--space-lg, 24px); }
.c-{{PREFIX}}-wizard-lane__label {
  font-size: 12px; color: var(--{{PREFIX}}-on-muted);
  margin-bottom: 8px; display: flex; justify-content: space-between;
}
.c-{{PREFIX}}-wizard-lane__track {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px;
}
.c-{{PREFIX}}-wizard-lane__step {
  background: var(--{{PREFIX}}-muted);
  border: 1px solid var(--{{PREFIX}}-border);
  border-radius: 8px; padding: 10px 8px; text-align: center;
  font-size: 12px; color: var(--{{PREFIX}}-on-muted);
}
.c-{{PREFIX}}-wizard-lane__step--done {
  border-color: var(--{{PREFIX}}-accent); color: var(--{{PREFIX}}-accent);
}
.c-{{PREFIX}}-wizard-lane__step--current {
  border-color: var(--{{PREFIX}}-primary);
  background: rgba(234, 88, 12, 0.12); color: var(--{{PREFIX}}-fg);
}
.c-{{PREFIX}}-wizard-lane__step-num {
  display: block; font-family: var(--{{PREFIX}}-font-display, inherit);
  font-size: 14px; font-weight: 700; margin-bottom: 2px;
}
