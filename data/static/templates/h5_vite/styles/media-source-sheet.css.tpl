/* MEDIA-SHEET:pipeline — copy into global.css or motion.css after prefix apply */

.c-{{PREFIX}}-media-sheet {
  position: fixed;
  inset: 0;
  z-index: 110;
  display: grid;
  align-items: end;
  padding: 16px;
  padding-bottom: calc(16px + var(--safe-bottom));
  background: rgba(15, 23, 42, 0.45);
  backdrop-filter: blur(4px);
}

.c-{{PREFIX}}-media-sheet__panel {
  width: 100%;
  max-width: 420px;
  margin: 0 auto;
  padding: 16px;
  border-radius: var(--{{PREFIX}}-radius-lg);
  background: var(--{{PREFIX}}-sheet);
  border: 1px solid var(--{{PREFIX}}-border);
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.18);
}

.c-{{PREFIX}}-media-sheet__title {
  margin: 0 0 4px;
  font-family: var(--{{PREFIX}}-font-display);
  font-size: 14px;
  font-weight: 700;
}

.c-{{PREFIX}}-media-sheet__sub {
  margin: 0 0 12px;
  font-size: 12px;
  line-height: 1.45;
  color: var(--{{PREFIX}}-on-muted);
}

.c-{{PREFIX}}-media-sheet__action {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  min-height: 48px;
  margin-bottom: 8px;
  padding: 12px 14px;
  border: 1px solid var(--{{PREFIX}}-border);
  border-radius: var(--{{PREFIX}}-radius-md);
  background: var(--{{PREFIX}}-card);
  color: var(--{{PREFIX}}-fg);
  font-family: var(--{{PREFIX}}-font-body);
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: transform 0.15s ease, background 0.15s ease;
}

.c-{{PREFIX}}-media-sheet__action:active {
  transform: scale(0.98);
}

.c-{{PREFIX}}-media-sheet__action .c-{{PREFIX}}-mark {
  width: 20px;
  height: 20px;
  color: var(--{{PREFIX}}-primary);
}

.c-{{PREFIX}}-media-sheet__cancel {
  width: 100%;
  min-height: 44px;
  margin-top: 4px;
  border: none;
  border-radius: var(--{{PREFIX}}-radius-md);
  background: transparent;
  color: var(--{{PREFIX}}-on-muted);
  font-family: var(--{{PREFIX}}-font-body);
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}
