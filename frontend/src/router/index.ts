import { createRouter, createWebHistory } from 'vue-router';
import { authGuard } from './guards';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/accounts' },
    { path: '/login', name: 'login', component: () => import('@/pages/LoginPage.vue'), meta: { public: true } },
    { path: '/accounts', name: 'accounts', component: () => import('@/pages/AccountsRiskPage.vue') },
    { path: '/models', name: 'models', component: () => import('@/pages/ModelEvalPage.vue') },
    { path: '/features', name: 'features', component: () => import('@/pages/FeaturesPage.vue') },
    { path: '/scores', name: 'scores', component: () => import('@/pages/ScoreBatchesPage.vue') },
    { path: '/:pathMatch(.*)*', redirect: '/accounts' },
  ],
  scrollBehavior: () => ({ top: 0 }),
});

router.beforeEach(authGuard);

export default router;
