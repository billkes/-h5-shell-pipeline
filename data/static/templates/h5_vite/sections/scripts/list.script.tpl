<script setup lang="ts">
import TopBar from '../components/TopBar.vue';
import TabBar from '../components/TabBar.vue';
import { useRunsLogic } from './{{VIEW_STEM}}.logic';

const {
  rows,
  courseChips,
  filterCourse,
  toggleCourse,
  openRun,
  goToHub,
  totalRuns,
  weekRuns,
  avgWpmKpi,
  sortLabel,
  dateRangeLabel,
  visibleCount,
} = useRunsLogic();
</script>
