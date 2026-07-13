/* PAGE-SCAFFOLD:pipeline — auto-synced; do not hand-edit */
.c-{{PREFIX}}-hub-hero { margin-bottom: var(--space-lg, 24px); }
.c-{{PREFIX}}-hub-hero__eyebrow {
  font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase;
  color: var(--{{PREFIX}}-secondary); margin-bottom: 8px;
}
.c-{{PREFIX}}-hub-hero__title {
  font-family: var(--{{PREFIX}}-font-display, inherit);
  font-size: 28px; font-weight: 700; line-height: 1.15; margin-bottom: 8px;
}
.c-{{PREFIX}}-hub-hero__sub {
  font-size: 13px; line-height: 1.5; color: var(--{{PREFIX}}-on-muted);
}
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
  font-size: 10px; color: var(--{{PREFIX}}-on-muted); margin-top: 4px;
  text-transform: uppercase; letter-spacing: 0.06em;
}
.c-{{PREFIX}}-wizard-lane { margin-bottom: var(--space-lg, 24px); }
.c-{{PREFIX}}-wizard-lane__label {
  font-size: 11px; color: var(--{{PREFIX}}-on-muted);
  margin-bottom: 8px; display: flex; justify-content: space-between;
}
.c-{{PREFIX}}-wizard-lane__track {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px;
}
.c-{{PREFIX}}-wizard-lane__step {
  background: var(--{{PREFIX}}-muted);
  border: 1px solid var(--{{PREFIX}}-border);
  border-radius: 8px; padding: 10px 8px; text-align: center;
  font-size: 10px; color: var(--{{PREFIX}}-on-muted);
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
.c-{{PREFIX}}-chip-rail {
  display: flex; gap: 8px; overflow-x: auto; scrollbar-width: none;
  margin-bottom: var(--space-lg, 24px); padding-bottom: 2px;
}
.c-{{PREFIX}}-chip-rail::-webkit-scrollbar { display: none; }
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
  font-size: 11px; line-height: 1.45; color: var(--{{PREFIX}}-on-muted);
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
.c-{{PREFIX}}-cta-stack {
  display: flex; flex-direction: column; gap: 8px; margin-bottom: var(--space-lg, 24px);
}
.c-{{PREFIX}}-section-head {
  display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;
}
.c-{{PREFIX}}-section-head__title {
  font-family: var(--{{PREFIX}}-font-display, inherit);
  font-size: 14px; font-weight: 700;
}
.c-{{PREFIX}}-draft-card {
  background: var(--{{PREFIX}}-card);
  border: 1px solid var(--{{PREFIX}}-border);
  border-radius: var(--{{PREFIX}}-radius-lg, 16px);
  padding: 16px; margin-bottom: 8px; cursor: pointer;
}
.c-{{PREFIX}}-draft-card__title { font-weight: 700; font-size: 14px; margin-bottom: 4px; }
.c-{{PREFIX}}-draft-card__meta { font-size: 11px; color: var(--{{PREFIX}}-on-muted); }
.c-{{PREFIX}}-draft-card__badge {
  font-size: 10px; font-weight: 700; padding: 4px 8px; border-radius: 999px;
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
.c-{{PREFIX}}-list-kpi {
  display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap;
}
.c-{{PREFIX}}-list-row {
  margin-bottom: 10px; display: flex; align-items: center;
  justify-content: space-between; min-height: 56px; cursor: pointer;
}
@media (prefers-reduced-motion: reduce) {
  .c-{{PREFIX}}-waveform__bar { animation: none !important; }
}
/* PAGE-SCAFFOLD:end */
