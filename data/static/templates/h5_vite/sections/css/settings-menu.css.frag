.c-{{PREFIX}}-settings-group-label {
  margin: 0 0 12px;
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--{{PREFIX}}-on-muted);
}
.c-{{PREFIX}}-settings-menu { display: flex; flex-direction: column; gap: 8px; margin-bottom: 18px; }
.c-{{PREFIX}}-settings-menu--tail { margin-bottom: 10px; }
.c-{{PREFIX}}-settings-row {
  width: 100%; min-height: 54px; padding: 0 14px;
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
  border: 1px solid var(--{{PREFIX}}-border); border-radius: var(--{{PREFIX}}-radius-md, 12px);
  background: var(--{{PREFIX}}-card); color: var(--{{PREFIX}}-fg);
  font-size: 14px; font-weight: 600; font-family: inherit; cursor: pointer;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.03);
}
.c-{{PREFIX}}-settings-row__lead {
  display: flex; align-items: center; gap: 10px; min-width: 0;
}
.c-{{PREFIX}}-settings-row__icon {
  width: 34px; height: 34px; flex-shrink: 0;
  display: grid; place-items: center; border-radius: 10px;
  background: var(--{{PREFIX}}-muted); color: var(--{{PREFIX}}-on-muted);
}
.c-{{PREFIX}}-settings-row__icon .c-{{PREFIX}}-mark { width: 18px; height: 18px; }
.c-{{PREFIX}}-settings-row__icon--primary {
  background: rgba(234, 88, 12, 0.14); color: var(--{{PREFIX}}-primary);
}
.c-{{PREFIX}}-settings-row__icon--danger {
  background: rgba(220, 38, 38, 0.12); color: var(--{{PREFIX}}-destructive);
}
.c-{{PREFIX}}-settings-row__chevron { flex-shrink: 0; color: var(--{{PREFIX}}-on-muted); }
.c-{{PREFIX}}-settings-row--danger { color: var(--{{PREFIX}}-destructive); }
.c-{{PREFIX}}-settings-row--danger .c-{{PREFIX}}-settings-row__chevron {
  color: rgba(220, 38, 38, 0.55);
}
.c-{{PREFIX}}-settings-dev {
  width: 100%; min-height: 44px; margin-top: 4px; padding: 10px 14px;
  border: 1px dashed rgba(234, 88, 12, 0.45); border-radius: var(--{{PREFIX}}-radius-md, 12px);
  background: rgba(234, 88, 12, 0.06); color: var(--{{PREFIX}}-primary);
  font-size: 12px; font-weight: 700; letter-spacing: 0.04em; font-family: inherit; cursor: pointer;
}
.c-{{PREFIX}}-settings-dialog { width: min(340px, 90vw); text-align: center; }
.c-{{PREFIX}}-settings-dialog__icon {
  width: 44px; height: 44px; margin: 0 auto 12px;
  display: grid; place-items: center; border-radius: 50%;
  background: rgba(220, 38, 38, 0.12); color: var(--{{PREFIX}}-destructive);
}
.c-{{PREFIX}}-settings-dialog__icon .c-{{PREFIX}}-mark { width: 22px; height: 22px; }
.c-{{PREFIX}}-settings-dialog__title {
  margin: 0 0 8px;
  font-family: var(--{{PREFIX}}-font-display, inherit);
  font-size: 16px; font-weight: 700; line-height: 1.25;
}
.c-{{PREFIX}}-settings-dialog__sub {
  margin: 0 0 18px; font-size: 13px; line-height: 1.5; color: var(--{{PREFIX}}-on-muted);
}
.c-{{PREFIX}}-settings-dialog__actions { display: flex; gap: 8px; }
.c-{{PREFIX}}-settings-dialog__actions .c-{{PREFIX}}-action { flex: 1; }
.c-{{PREFIX}}-settings-dialog__confirm { background: var(--{{PREFIX}}-destructive); }
