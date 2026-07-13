import { createRouter, createWebHashHistory } from 'vue-router';
import SplashView from '../views/SplashView.vue';
import WelcomeView from '../views/WelcomeView.vue';

export const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/splash', component: SplashView },
    { path: '/welcome', component: WelcomeView },
    { path: '/:pathMatch(.*)*', redirect: '/splash' },
  ],
});
