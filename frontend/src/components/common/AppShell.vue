<script setup lang="ts">
import { onBeforeUnmount, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import { ROLE_LABELS, ROLE_SCOPE } from '@/constants/roles';

const auth = useAuthStore();
const router = useRouter();

const pages = [
  { code: '01', label: '客户风险图', path: '/accounts' },
  { code: '02', label: '模型评估', path: '/models' },
  { code: '03', label: '特征与权重', path: '/features' },
  { code: '04', label: '阈值策略', path: '/scores' },
];

function logout() {
  auth.logout();
  router.push('/login');
}

function onUnauthorized() {
  router.push('/login');
}

onMounted(() => window.addEventListener('churnmod:unauthorized', onUnauthorized));
onBeforeUnmount(() => window.removeEventListener('churnmod:unauthorized', onUnauthorized));
</script>

<template>
  <div class="shell">
    <aside class="rail">
      <div class="rail__brand">
        <span class="rail__mark">Churn Chart</span>
        <span class="rail__sub">安澜云服务 · 客户成功部<br />流失预判海图</span>
      </div>

      <svg class="rail__compass" viewBox="0 0 160 160" role="img" aria-label="罗盘刻度">
        <circle cx="80" cy="80" r="64" fill="none" stroke="oklch(72% 0.04 88 / 0.5)" stroke-width="1" />
        <circle cx="80" cy="80" r="52" fill="none" stroke="oklch(72% 0.04 88 / 0.28)" stroke-width="1" />
        <circle cx="80" cy="80" r="26" fill="none" stroke="oklch(72% 0.04 88 / 0.3)" stroke-width="1" />
        <g stroke="oklch(78% 0.035 90 / 0.6)" stroke-width="1">
          <line v-for="index in 36" :key="index" x1="80" y1="16" x2="80" y2="23"
            :transform="`rotate(${index * 10} 80 80)`" />
        </g>
        <path d="M80 26 L88 80 L80 134 L72 80 Z" fill="oklch(86% 0.045 84 / 0.85)" />
        <path d="M26 80 L80 72 L134 80 L80 88 Z" fill="oklch(72% 0.05 86 / 0.55)" />
        <circle cx="80" cy="80" r="3" fill="oklch(94% 0.02 90)" />
        <text x="80" y="12" text-anchor="middle" font-size="9" fill="oklch(82% 0.04 88)" font-family="monospace">N</text>
      </svg>

      <div>
        <p class="rail__contents">Contents · 海图分幅</p>
        <nav class="rail__nav">
          <RouterLink v-for="page in pages" :key="page.path" :to="page.path" class="rail__link" active-class="is-active">
            <span class="rail__link-code">{{ page.code }}</span>
            <span class="rail__link-label">{{ page.label }}</span>
          </RouterLink>
        </nav>
      </div>

      <div class="rail__foot">
        <p v-if="auth.user"><strong>{{ auth.user.display_name }}</strong> · {{ ROLE_LABELS[auth.role] }}</p>
        <p v-if="auth.user">{{ ROLE_SCOPE[auth.role] }}</p>
        <p v-if="auth.user">{{ auth.user.email }}</p>
        <button class="rail__logout" type="button" @click="logout">退出登录</button>
      </div>
    </aside>
    <main class="page">
      <slot />
    </main>
  </div>
</template>
