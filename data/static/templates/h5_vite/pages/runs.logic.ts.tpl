import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';
import { formatShortDate, formatShortDateTime } from '../lib/uiLocale';
import { getPlan, getSections, listRuns } from '../store/appStore';

function formatDuration(startedAt: number, endedAt: number): string {
  const sec = Math.max(0, Math.round((endedAt - startedAt) / 1000));
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}m ${String(s).padStart(2, '0')}s`;
}

export function useRunsLogic() {
  const router = useRouter();
  const filterCourse = ref('');
  const sortNewest = ref(true);

  const allRuns = computed(() => listRuns());

  const rows = computed(() => {
    let list = allRuns.value.map((r) => {
      const plan = getPlan(r.planId);
      const sections = getSections(r.planId);
      const title = sections[0]?.title || plan?.courseLabel || 'Rehearsal';
      return {
        id: r.id,
        title,
        courseTag: plan?.courseLabel || 'Unknown',
        dateLabel: formatShortDateTime(r.startedAt),
        durationLabel: formatDuration(r.startedAt, r.endedAt || r.startedAt),
        avgWpm: Math.round(r.avgWpm),
        overtimeCount: r.overtimeSegments.length,
        sectionCount: sections.length || r.sectionTimings?.length || 0,
        hasNotes: Boolean(r.notes?.trim()),
        startedAt: r.startedAt,
      };
    });
    if (filterCourse.value) {
      list = list.filter((r) => r.courseTag === filterCourse.value);
    }
    list.sort((a, b) => (sortNewest.value ? b.startedAt - a.startedAt : a.startedAt - b.startedAt));
    return list;
  });

  const courseChips = computed(() => {
    const set = new Set(allRuns.value.map((r) => getPlan(r.planId)?.courseLabel).filter(Boolean) as string[]);
    return ['', ...Array.from(set)];
  });

  const totalRuns = computed(() => allRuns.value.length);
  const weekRuns = computed(() => {
    const weekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
    return allRuns.value.filter((r) => r.startedAt >= weekAgo).length;
  });
  const avgWpmKpi = computed(() => {
    if (!allRuns.value.length) return '—';
    const avg = allRuns.value.reduce((sum, r) => sum + r.avgWpm, 0) / allRuns.value.length;
    return String(Math.round(avg));
  });
  const sortLabel = computed(() => (sortNewest.value ? 'Newest first' : 'Oldest first'));
  const dateRangeLabel = computed(() => {
    if (!allRuns.value.length) return '—';
    const ts = allRuns.value.map((r) => r.startedAt);
    const min = new Date(Math.min(...ts));
    const max = new Date(Math.max(...ts));
    const fmt = formatShortDate;
    return `${fmt(min)} – ${fmt(max)}`;
  });
  const visibleCount = computed(() => rows.value.length);

  function toggleCourse(c: string) {
    filterCourse.value = filterCourse.value === c ? '' : c;
  }

  function openRun(id: string) {
    router.push(`/run/${id}`);
  }

  function goToHub() {
    router.push('/hub');
  }

  return {
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
    sortNewest,
  };
}
