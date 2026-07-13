.c-{{PREFIX}}-settings-menu { display: flex; flex-direction: column; gap: 8px; margin-bottom: 24px; }
.c-{{PREFIX}}-settings-row {
  width: 100%; min-height: 52px; padding: 0 16px;
  display: flex; align-items: center; justify-content: space-between;
  border: 1px solid var(--{{PREFIX}}-border); border-radius: var(--{{PREFIX}}-radius-md, 12px);
  background: var(--{{PREFIX}}-card); color: var(--{{PREFIX}}-fg);
  font-size: 14px; font-weight: 600; font-family: inherit; cursor: pointer;
}
.c-{{PREFIX}}-settings-row--danger { color: var(--{{PREFIX}}-destructive); }
