/* LEGAL:pipeline — auto-synced; do not hand-edit */
.c-{{PREFIX}}-legal-veil {
  position: fixed;
  inset: 0;
  z-index: 60;
  background: rgba(0, 0, 0, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}
.c-{{PREFIX}}-legal-card {
  width: min(90vw, 340px);
  max-height: 85vh;
  background: var(--{{PREFIX}}-sheet);
  border-radius: var(--{{PREFIX}}-radius-lg, 16px);
  border: 1px solid var(--{{PREFIX}}-border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  text-align: left;
}
.c-{{PREFIX}}-legal-header {
  flex-shrink: 0;
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 12px 12px 8px 16px;
  border-bottom: 1px solid var(--{{PREFIX}}-border);
}
.c-{{PREFIX}}-legal-title {
  flex: 1;
  min-width: 0;
  margin: 0;
  padding-top: 4px;
  font-size: 16px;
  font-weight: 600;
  line-height: 1.25;
}
.c-{{PREFIX}}-legal-close {
  flex-shrink: 0;
  width: 44px;
  height: 44px;
  margin: 0;
  padding: 0;
  border: none;
  border-radius: var(--{{PREFIX}}-radius-md, 12px);
  background: color-mix(in srgb, var(--{{PREFIX}}-fg) 8%, transparent);
  color: var(--{{PREFIX}}-fg);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}
.c-{{PREFIX}}-legal-close:active {
  background: color-mix(in srgb, var(--{{PREFIX}}-fg) 16%, transparent);
}
.c-{{PREFIX}}-legal-scroll {
  flex: 1;
  min-height: 0;
  padding: 16px;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  mask-image: linear-gradient(to bottom, #000 calc(100% - 28px), transparent 100%);
  scrollbar-width: none;
}
.c-{{PREFIX}}-legal-scroll::-webkit-scrollbar {
  display: none;
  width: 0;
  height: 0;
}
.c-{{PREFIX}}-legal-meta {
  margin: 0 0 12px;
  font-size: 11px;
  line-height: 1.4;
  color: var(--{{PREFIX}}-on-muted);
}
.c-{{PREFIX}}-legal-section {
  margin: 16px 0 8px;
  font-size: 14px;
  font-weight: 600;
  line-height: 1.3;
  color: var(--{{PREFIX}}-fg);
}
.c-{{PREFIX}}-legal-section:first-child {
  margin-top: 0;
}
.c-{{PREFIX}}-legal-para {
  margin: 0 0 12px;
  font-size: 11px;
  line-height: 1.55;
  color: var(--{{PREFIX}}-on-muted);
}
.c-{{PREFIX}}-legal-para:last-child {
  margin-bottom: 0;
}
/* LEGAL:end */
