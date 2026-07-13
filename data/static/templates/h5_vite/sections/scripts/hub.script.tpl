<script setup lang="ts">
import TopBar from '../components/TopBar.vue';
import TabBar from '../components/TabBar.vue';
import { useHubLogic } from './{{VIEW_STEM}}.logic';

const {
  drafts,
  draftCount,
  lastRunLabel,
  avgWpmLabel,
  paceFill,
  courseChips,
  activeChip,
  setChip,
  wizardStep,
  wizardStepLabel,
  wizardSteps,
  startWizard,
  importDemo,
  openDraft,
} = useHubLogic();
</script>
