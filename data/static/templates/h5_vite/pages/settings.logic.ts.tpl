import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { BOOTSTRAP_KEY } from '../store/defaultSeed';
import { loadWallet } from '../store/data';
import { STORAGE } from '../store/keys';

export function useSettingsLogic() {
  const router = useRouter();
  const balance = ref(0);
  const freeRemaining = ref(2);
  const showClear = ref(false);
  let versionPressTimer: ReturnType<typeof setTimeout> | null = null;

  function refreshWallet() {
    const w = loadWallet();
    balance.value = w.coinBalance;
    freeRemaining.value = w.freeRemaining;
  }

  onMounted(refreshWallet);

  function openStore() {
    router.push('/store');
  }

  function openLegal(doc: 'privacy' | 'terms') {
    router.push({ path: '/legal', query: { doc, base: '/settings' } });
  }

  function openPlaza() {
    router.push('/plaza');
  }

  function onVerTouchStart() {
    versionPressTimer = setTimeout(() => router.push('/plaza'), 3000);
  }

  function onVerTouchEnd() {
    if (versionPressTimer) clearTimeout(versionPressTimer);
  }

  function clearData() {
    localStorage.removeItem(STORAGE.plans);
    localStorage.removeItem(STORAGE.runs);
    localStorage.removeItem(STORAGE.exports);
    localStorage.setItem(BOOTSTRAP_KEY, 'true');
    showClear.value = false;
  }

  return {
    balance,
    freeRemaining,
    showClear,
    openStore,
    openLegal,
    openPlaza,
    onVerTouchStart,
    onVerTouchEnd,
    clearData,
  };
}
