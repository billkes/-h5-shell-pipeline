import { STORAGE } from './keys';
import {
  loadPlans,
  loadRuns,
  savePlans,
  saveRuns,
  type LiveRun,
  type RehearsalPlan,
} from './data';

export const BOOTSTRAP_KEY = '{{PREFIX}}_bootstrap_v1';

/** Agent: return 1–3 English rehearsal plans aligned with product doc 演示数据. */
export function buildDefaultPlans(): RehearsalPlan[] {
  return [];
}

/** Agent: return 1–3 runs linked to buildDefaultPlans() plan ids. */
export function buildDefaultRuns(_plans: RehearsalPlan[]): LiveRun[] {
  return [];
}

/** Silent first-launch seed — called from Welcome continueFlow (and Hub onMounted fallback). */
export function ensureBootstrapData(): void {
  if (localStorage.getItem(BOOTSTRAP_KEY) === 'true') return;
  if (loadPlans().length > 0 || loadRuns().length > 0) return;
  const plans = buildDefaultPlans();
  if (!plans.length) return;
  const runs = buildDefaultRuns(plans);
  savePlans(plans);
  saveRuns(runs);
  localStorage.setItem(BOOTSTRAP_KEY, 'true');
  localStorage.setItem(STORAGE.exports, '[]');
}
