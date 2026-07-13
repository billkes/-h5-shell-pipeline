import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';
import { bridgeCall, showSnack } from '../bridge';

/** Bridge Plaza QA only — not store catalog SKU. */
export const PLAZA_TEST_PURCHASE_PRODUCT_ID = '311400';

export type PlazaActionState = 'idle' | 'calling' | 'success' | 'error' | 'cancelled';

export type PlazaResult = {
  action: string;
  state: PlazaActionState;
  title: string;
  detail: string;
  raw: string;
};

type ActionMeta = { label: string; hint: string; group: string };

const ACTION_META: Record<string, ActionMeta> = {
  shellReady: { label: 'shellReady', hint: 'Confirm native shell handshake', group: 'shell' },
  getDeviceInfo: { label: 'getDeviceInfo', hint: 'Read safe-area and device flags', group: 'shell' },
  copyToClipboard: { label: 'copyToClipboard', hint: 'Copy QA label to pasteboard', group: 'shell' },
  readFile: { label: 'readFile', hint: 'Read qa/test.txt from app sandbox', group: 'files' },
  writeFile: { label: 'writeFile', hint: 'Write qa/test.txt into app sandbox', group: 'files' },
  pickImage: { label: 'pickImage', hint: 'Open system photo picker', group: 'media' },
  saveImage: { label: 'saveImage', hint: 'Persist picked image to sandbox', group: 'media' },
  mediaServe: { label: 'mediaServe', hint: 'Resolve bundled asset URL', group: 'media' },
  purchase: { label: 'Test purchase', hint: `Sandbox IAP · SKU ${PLAZA_TEST_PURCHASE_PRODUCT_ID}`, group: 'iap' },
  restorePurchases: { label: 'Restore purchases', hint: 'Replay StoreKit transactions', group: 'iap' },
  openLegal: { label: 'openLegal', hint: 'Native legal bridge (QA only)', group: 'legal' },
};

const GROUPS = [
  { id: 'shell', label: 'Shell' },
  { id: 'files', label: 'Files' },
  { id: 'media', label: 'Media' },
  { id: 'iap', label: 'In-App Purchase' },
  { id: 'legal', label: 'Legal' },
] as const;

const ACTIONS = Object.keys(ACTION_META);

function isCancelled(msg: string): boolean {
  const m = msg.toLowerCase();
  return m === 'user_cancelled' || m.includes('cancel');
}

function buildPayload(action: string, appName: string, assetPath: string) {
  if (action === 'writeFile') return { path: 'qa/test.txt', base64: btoa(appName) };
  if (action === 'readFile') return { path: 'qa/test.txt' };
  if (action === 'purchase') return { productId: PLAZA_TEST_PURCHASE_PRODUCT_ID };
  if (action === 'mediaServe') return { path: assetPath };
  if (action === 'copyToClipboard') return { text: `${appName} QA` };
  return {};
}

function summarizeSuccess(action: string, res: unknown): { title: string; detail: string } {
  const payload = (res && typeof res === 'object' ? res : {}) as Record<string, string>;
  if (action === 'purchase') {
    const pid = payload.productId || PLAZA_TEST_PURCHASE_PRODUCT_ID;
    const txn = payload.transactionId || '';
    return {
      title: 'Purchase confirmed',
      detail: txn
        ? `Product ${pid} charged · Transaction ${txn}`
        : `Product ${pid} purchase completed`,
    };
  }
  if (action === 'restorePurchases') {
    return { title: 'Restore complete', detail: 'StoreKit finished restoring purchases' };
  }
  if (action === 'copyToClipboard') {
    return { title: 'Copied', detail: 'Clipboard updated' };
  }
  if (action === 'pickImage' && payload.path) {
    return { title: 'Image picked', detail: payload.path };
  }
  if (action === 'saveImage' && payload.saved) {
    return { title: 'Image saved', detail: payload.path || 'Saved to sandbox' };
  }
  if (action === 'readFile' && payload.base64) {
    return { title: 'File read', detail: payload.path || 'qa/test.txt' };
  }
  if (action === 'writeFile') {
    return { title: 'File written', detail: payload.path || 'qa/test.txt' };
  }
  if (action === 'mediaServe' && payload.url) {
    return { title: 'Media URL ready', detail: payload.url };
  }
  if (action === 'openLegal' && payload.url) {
    return { title: 'Legal opened', detail: payload.url };
  }
  return { title: 'Bridge OK', detail: `${action} returned successfully` };
}

function snackForResult(result: PlazaResult): string | null {
  if (result.state === 'success' && (result.action === 'purchase' || result.action === 'restorePurchases')) {
    return result.title;
  }
  if (result.state === 'error') return result.detail || result.title;
  if (result.state === 'cancelled') return 'Purchase cancelled';
  return null;
}

export function usePlazaLogic(appName = '{{APP_NAME}}', assetPath = 'img/{{PREFIX}}_rhythm_frame.png') {
  const router = useRouter();
  const states = ref<Record<string, PlazaActionState>>({});
  const lastResult = ref<PlazaResult | null>(null);
  const log = ref('');
  const busy = ref(false);

  const groupedActions = computed(() =>
    GROUPS.map((group) => ({
      ...group,
      actions: ACTIONS.filter((id) => ACTION_META[id]?.group === group.id).map((id) => ({
        id,
        ...ACTION_META[id],
        state: states.value[id] || 'idle',
      })),
    })).filter((g) => g.actions.length),
  );

  function setState(action: string, state: PlazaActionState) {
    states.value = { ...states.value, [action]: state };
  }

  async function call(action: string) {
    if (busy.value) return;
    busy.value = true;
    setState(action, 'calling');
    lastResult.value = null;
    try {
      const res = await bridgeCall(action, buildPayload(action, appName, assetPath));
      const summary = summarizeSuccess(action, res);
      const raw = JSON.stringify(res, null, 2);
      log.value = raw;
      setState(action, 'success');
      lastResult.value = {
        action,
        state: 'success',
        title: summary.title,
        detail: summary.detail,
        raw,
      };
      const snack = snackForResult(lastResult.value);
      if (snack) showSnack(snack);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      log.value = msg;
      if (isCancelled(msg)) {
        setState(action, 'cancelled');
        lastResult.value = {
          action,
          state: 'cancelled',
          title: 'Cancelled',
          detail: 'No charge was made',
          raw: msg,
        };
        if (action === 'purchase' || action === 'restorePurchases') showSnack('Purchase cancelled');
      } else {
        setState(action, 'error');
        lastResult.value = {
          action,
          state: 'error',
          title: 'Bridge error',
          detail: msg || 'Unknown failure',
          raw: msg,
        };
        showSnack(msg || 'Bridge call failed');
      }
    } finally {
      busy.value = false;
    }
  }

  function goBack() {
    router.back();
  }

  return {
    groupedActions,
    lastResult,
    log,
    busy,
    call,
    goBack,
  };
}
