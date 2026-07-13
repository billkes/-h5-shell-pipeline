.c-{{PREFIX}}-bento {
  display: grid; grid-template-columns: 1fr 1fr; gap: 8px;
  margin-bottom: var(--space-lg, 24px);
}
.c-{{PREFIX}}-bento__wide { grid-column: 1 / -1; }
.c-{{PREFIX}}-bento-tile {
  background: var(--{{PREFIX}}-card);
  border: 1px solid var(--{{PREFIX}}-border);
  border-radius: var(--{{PREFIX}}-radius-lg, 16px);
  padding: 16px;
}
.c-{{PREFIX}}-bento-tile__icon {
  width: 36px; height: 36px; display: flex; align-items: center; justify-content: center;
  border-radius: 8px; background: rgba(234, 88, 12, 0.15);
  color: var(--{{PREFIX}}-primary); margin-bottom: 8px;
}
.c-{{PREFIX}}-bento-tile__icon--green {
  background: rgba(5, 150, 105, 0.15); color: var(--{{PREFIX}}-accent);
}
.c-{{PREFIX}}-bento-tile__icon--warn {
  background: rgba(220, 38, 38, 0.15); color: var(--{{PREFIX}}-destructive);
}
.c-{{PREFIX}}-bento-tile__title {
  font-family: var(--{{PREFIX}}-font-display, inherit);
  font-size: 13px; font-weight: 700; margin-bottom: 4px;
}
.c-{{PREFIX}}-bento-tile__desc {
  font-size: 12px; line-height: 1.45; color: var(--{{PREFIX}}-on-muted);
}
.c-{{PREFIX}}-pace-gauge {
  display: flex; align-items: center; gap: 8px; margin-top: 8px;
}
.c-{{PREFIX}}-pace-gauge__bar {
  flex: 1; height: 6px; border-radius: 999px;
  background: var(--{{PREFIX}}-muted); overflow: hidden;
}
.c-{{PREFIX}}-pace-gauge__fill {
  height: 100%; background: linear-gradient(90deg, var(--{{PREFIX}}-accent), var(--{{PREFIX}}-secondary));
  border-radius: 999px;
}
.c-{{PREFIX}}-pace-gauge__label {
  font-size: 12px; font-weight: 700; color: var(--{{PREFIX}}-accent);
}
.c-{{PREFIX}}-waveform {
  display: flex; align-items: flex-end; gap: 3px; height: 32px; margin-top: 8px;
}
.c-{{PREFIX}}-waveform__bar {
  flex: 1; border-radius: 2px; background: var(--{{PREFIX}}-primary);
  animation: {{PREFIX}}-wave 1.2s ease-in-out infinite;
}
.c-{{PREFIX}}-waveform__bar:nth-child(1) { height: 40%; animation-delay: 0s; }
.c-{{PREFIX}}-waveform__bar:nth-child(2) { height: 70%; animation-delay: 0.1s; }
.c-{{PREFIX}}-waveform__bar:nth-child(3) { height: 55%; animation-delay: 0.2s; }
.c-{{PREFIX}}-waveform__bar:nth-child(4) { height: 90%; animation-delay: 0.3s; }
.c-{{PREFIX}}-waveform__bar:nth-child(5) { height: 45%; animation-delay: 0.4s; }
.c-{{PREFIX}}-waveform__bar:nth-child(6) { height: 65%; animation-delay: 0.5s; }
.c-{{PREFIX}}-waveform__bar:nth-child(7) { height: 35%; animation-delay: 0.6s; }
@keyframes {{PREFIX}}-wave {
  0%, 100% { transform: scaleY(1); }
  50% { transform: scaleY(0.5); }
}
