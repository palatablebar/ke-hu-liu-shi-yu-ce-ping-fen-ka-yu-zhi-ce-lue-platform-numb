<script setup lang="ts">
import { ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();

const email = ref('admin@churnmod.io');
const password = ref('Demo@2026');
const error = ref('');

const demoAccounts = [
  { email: 'admin@churnmod.io', role: '客户成功负责人 · 阈值发布' },
  { email: 'analyst@churnmod.io', role: '数据分析师 · 训练调参' },
  { email: 'csm@churnmod.io', role: '客户成功经理 · 只读自己名单' },
];

async function submit() {
  error.value = '';
  try {
    await auth.login(email.value.trim(), password.value);
    const next = typeof route.query.next === 'string' ? route.query.next : '/accounts';
    router.push(next);
  } catch (err) {
    error.value = err instanceof Error ? err.message : '登录失败';
  }
}

function fillDemo(target: string) {
  email.value = target;
  password.value = 'Demo@2026';
}
</script>

<template>
  <div class="login">
    <section class="login__cover">
      <p class="login__plate">MMXXVI · 安澜云服务客户成功部 · 海图第 240 分幅</p>
      <h1 class="login__title">流失预判<br />海图</h1>
      <p class="login__lede">
        用量、工单、账单三类月度特征汇入一张评分卡：先算概率，再按阈值与预算画出触达航线；
        名单上的每一家，都带得走「为什么高风险」的三条理由。
      </p>
      <svg class="login__contours" viewBox="0 0 520 190" role="img" aria-label="等深线">
        <g fill="none" stroke="oklch(78% 0.04 88 / 0.5)" stroke-width="1">
          <path d="M10 150 C 80 108, 150 168, 220 132 S 360 90, 430 126 S 500 150, 512 140" />
          <path d="M10 130 C 78 92, 150 148, 224 114 S 356 74, 424 106 S 500 128, 512 118" />
          <path d="M10 110 C 76 76, 148 128, 228 96 S 352 58, 418 86 S 498 106, 512 96" />
          <path d="M10 90 C 74 60, 146 108, 232 78 S 348 42, 412 66 S 496 84, 512 74" />
          <path d="M150 60 C 200 40, 260 62, 300 46 S 380 26, 420 40" stroke-dasharray="4 5" />
        </g>
        <g fill="oklch(86% 0.045 84 / 0.9)">
          <circle cx="120" cy="146" r="2.5" /><circle cx="258" cy="106" r="2.5" /><circle cx="372" cy="82" r="2.5" />
        </g>
        <text x="120" y="170" text-anchor="middle" font-size="9" fill="oklch(78% 0.03 88)">ACC-0007</text>
        <text x="258" y="128" text-anchor="middle" font-size="9" fill="oklch(78% 0.03 88)">ACC-0130</text>
        <text x="372" y="104" text-anchor="middle" font-size="9" fill="oklch(78% 0.03 88)">ACC-0211</text>
      </svg>
      <p class="small" style="color: oklch(75% 0.03 88)">
        去年整体流失 14%；这张图把「感觉要跑」变成可复核的概率、分档与预算约束。
      </p>
    </section>

    <section class="login__form">
      <div>
        <p class="eyebrow">Sign in · 进入海图室</p>
        <h2 class="login__form-title">核对身份</h2>
        <p class="small muted" style="margin-top: 7px">
          分析同事用 analyst 训练模型；CSM 只能看到自己名下的客户名单（服务端同样过滤）。
        </p>
      </div>

      <form class="stack" @submit.prevent="submit">
        <div class="form-row">
          <label for="email">邮箱</label>
          <input id="email" v-model="email" class="input" type="email" autocomplete="username" required />
        </div>
        <div class="form-row">
          <label for="password">密码</label>
          <input id="password" v-model="password" class="input" type="password" autocomplete="current-password" required />
        </div>
        <p v-if="error" class="form-error">{{ error }}</p>
        <button class="btn btn--primary" type="submit" :disabled="auth.loading">
          {{ auth.loading ? '核对中…' : '进入海图' }}
        </button>
      </form>

      <div class="login__hint">
        <p style="margin-bottom: 6px">演示账号（密码统一 <span class="numeral">Demo@2026</span>）</p>
        <div class="stack" style="gap: 5px">
          <button
            v-for="account in demoAccounts"
            :key="account.email"
            type="button"
            class="btn btn--ghost btn--small"
            style="justify-content: space-between"
            @click="fillDemo(account.email)"
          >
            <span>{{ account.email }}</span>
            <span class="small muted">{{ account.role }}</span>
          </button>
        </div>
      </div>
    </section>
  </div>
</template>
