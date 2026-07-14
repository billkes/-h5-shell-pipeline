import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { ensureBootstrapData } from '../store/defaultSeed';

export function useWelcomeLogic() {
  const router = useRouter();
  const agreed = ref(false);
  const legalDoc = ref<'privacy' | 'terms' | null>(null);

  function openLegal(doc: 'privacy' | 'terms') {
    legalDoc.value = doc;
  }

  function closeLegal() {
    legalDoc.value = null;
  }

  function continueFlow() {
    ensureBootstrapData();
    localStorage.setItem('{{PREFIX}}_welcome_v1', 'true');
    router.replace('/hub');
  }

  return { agreed, legalDoc, openLegal, closeLegal, continueFlow };
}
