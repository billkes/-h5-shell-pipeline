import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { ensureBootstrapData } from '../store/defaultSeed';

export function useWelcomeLogic() {
  const router = useRouter();
  const agreed = ref(false);

  function openLegal(doc: 'privacy' | 'terms') {
    router.push({ path: '/legal', query: { doc, base: '/welcome' } });
  }

  function continueFlow() {
    ensureBootstrapData();
    localStorage.setItem('{{PREFIX}}_welcome_v1', 'true');
    router.replace('/hub');
  }

  return { agreed, openLegal, continueFlow };
}
