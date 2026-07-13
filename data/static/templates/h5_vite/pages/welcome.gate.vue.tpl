<!-- SCAFFOLD:pipeline:start — sync_h5_page_scaffold; do not hand-edit template -->
<template>
  <div class="page-full">
    <div class="c-{{PREFIX}}-welcome">
      <h1 class="c-{{PREFIX}}-welcome__title welcome-title">Welcome to {{APP_NAME}}</h1>
      <p class="c-{{PREFIX}}-welcome__sub welcome-intro">{{WELCOME_INTRO}}</p>
      <ul class="c-{{PREFIX}}-welcome-trust">
        <li>{{TRUST_BULLET_1}}</li>
        <li>{{TRUST_BULLET_2}}</li>
      </ul>
      <p class="c-{{PREFIX}}-welcome-age">You must be 18 years or older to use this app.</p>
      <label class="c-{{PREFIX}}-welcome__check">
        <input v-model="agreed" type="checkbox" />
        <span>
          I agree to the
          <button type="button" class="c-{{PREFIX}}-link" @click="openLegal('privacy')">Privacy Agreement</button>
          and
          <button type="button" class="c-{{PREFIX}}-link" @click="openLegal('terms')">User Agreement</button>.
        </span>
      </label>
      <button class="c-{{PREFIX}}-action" type="button" :disabled="!agreed" @click="continueFlow">Continue</button>
    </div>
  </div>
</template>
<!-- SCAFFOLD:pipeline:end -->
<script setup lang="ts">
import { useWelcomeLogic } from './WelcomeView.logic';

const { agreed, openLegal, continueFlow } = useWelcomeLogic();
</script>
