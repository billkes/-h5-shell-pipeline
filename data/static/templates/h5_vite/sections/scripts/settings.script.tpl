<script setup lang="ts">
import TopBar from '../components/TopBar.vue';
import TabBar from '../components/TabBar.vue';
import { useSettingsLogic } from './{{VIEW_STEM}}.logic';

const {
  balance,
  freeRemaining,
  showClear,
  openStore,
  openLegal,
  openPlaza,
  onVerTouchStart,
  onVerTouchEnd,
  clearData,
} = useSettingsLogic();
</script>
