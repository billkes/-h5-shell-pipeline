import { createApp } from 'vue';
import App from './App.vue';
import { router } from './router';
import { attachUiNamespace } from './bridge';
import './styles/global.css';

const cap = '{{PREFIX_CAP}}';
attachUiNamespace(cap);

createApp(App).use(router).mount('#app');
