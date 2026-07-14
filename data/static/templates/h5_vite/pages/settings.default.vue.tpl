<!-- SCAFFOLD:pipeline:start — sync_h5_page_scaffold; do not hand-edit template -->
<template>
  <div>
    <TopBar title="{{SETTINGS_TITLE}}" />
    <div class="page-shell" data-{{PREFIX}}-landmark="settings-body">
      <div class="c-{{PREFIX}}-tile" style="margin-bottom:16px">
        <div style="font-size:12px;color:var(--{{PREFIX}}-on-muted)">Coins: {{ balance }} · Free exports: {{ freeRemaining }}</div>
      </div>
      <button class="c-{{PREFIX}}-tile" type="button" style="width:100%;text-align:left;margin-bottom:8px" @click="openStore">Coin Store</button>
      <button class="c-{{PREFIX}}-tile" type="button" style="width:100%;text-align:left;margin-bottom:8px" @click="openLegal('privacy')">Privacy Agreement</button>
      <button class="c-{{PREFIX}}-tile" type="button" style="width:100%;text-align:left;margin-bottom:8px" @click="openLegal('terms')">User Agreement</button>
      <button class="c-{{PREFIX}}-tile" type="button" style="width:100%;text-align:left;margin-bottom:8px;color:var(--{{PREFIX}}-destructive)" @click="showClear = true">Clear Rehearsal Data</button>
      <!-- H5_PLAZA_DEV_ENTRANCE_START -->
      <button class="c-{{PREFIX}}-action c-{{PREFIX}}-action--secondary" type="button" style="width:100%;margin-top:16px" @click="openPlaza">Dev: Bridge Plaza</button>
      <!-- H5_PLAZA_DEV_ENTRANCE_END -->
      <p
        style="text-align:center;color:var(--{{PREFIX}}-on-muted);font-size:12px;margin-top:32px"
        @touchstart="onVerTouchStart"
        @touchend="onVerTouchEnd"
      >Version 1.0.0</p>
    </div>
    <TabBar />
    <div v-if="showClear" class="c-{{PREFIX}}-dialog-veil" @click.self="showClear = false">
      <div class="c-{{PREFIX}}-dialog">
        <p>Delete all rehearsals?</p>
        <div style="display:flex;gap:8px;margin-top:16px">
          <button class="c-{{PREFIX}}-action c-{{PREFIX}}-action--secondary" type="button" style="flex:1" @click="showClear = false">Cancel</button>
          <button class="c-{{PREFIX}}-action" type="button" style="flex:1" @click="clearData">Clear</button>
        </div>
      </div>
    </div>
    <LegalOverlay v-if="legalDoc" :doc="legalDoc" @close="closeLegal" />
  </div>
</template>
<!-- SCAFFOLD:pipeline:end -->

<script setup lang="ts">
import LegalOverlay from '../components/LegalOverlay.vue';
import TopBar from '../components/TopBar.vue';
import TabBar from '../components/TabBar.vue';
import { useSettingsLogic } from './{{VIEW_STEM}}.logic';

const {
  balance,
  freeRemaining,
  showClear,
  legalDoc,
  openStore,
  openLegal,
  closeLegal,
  openPlaza,
  onVerTouchStart,
  onVerTouchEnd,
  clearData,
} = useSettingsLogic();
</script>
