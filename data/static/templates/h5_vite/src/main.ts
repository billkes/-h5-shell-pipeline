import { createApp } from 'vue';
import App from './App.vue';
import { router } from './router';
import { attachUiNamespace } from './bridge';
import './styles/global.css';
import { ensureBootstrapData } from './store/defaultSeed';

const cap = '{{PREFIX_CAP}}';
attachUiNamespace(cap);

ensureBootstrapData();

createApp(App).use(router).mount('#app');
