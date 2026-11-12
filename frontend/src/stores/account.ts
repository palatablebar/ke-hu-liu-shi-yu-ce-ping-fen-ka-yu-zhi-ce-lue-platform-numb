import { defineStore } from 'pinia';
import { ref } from 'vue';
import type { AccountDetail, AccountPage } from '@/types/account';
import * as api from '@/api/account';

export const useAccountStore = defineStore('account', () => {
  const page = ref<AccountPage | null>(null);
  const detail = ref<AccountDetail | null>(null);
  const detailLoading = ref(false);
  const loading = ref(false);
  const error = ref('');

  async function load(search = '', band = '', pageNo = 1, pageSize = 20): Promise<void> {
    loading.value = true;
    error.value = '';
    try {
      page.value = await api.fetchRiskList({ search, band, page: pageNo, pageSize });
    } catch (err) {
      error.value = err instanceof Error ? err.message : '加载客户风险名单失败';
    } finally {
      loading.value = false;
    }
  }

  async function loadDetail(code: string): Promise<void> {
    detailLoading.value = true;
    try {
      detail.value = await api.fetchAccount(code);
    } catch (err) {
      detail.value = null;
      error.value = err instanceof Error ? err.message : '加载客户详情失败';
    } finally {
      detailLoading.value = false;
    }
  }

  return { page, detail, detailLoading, loading, error, load, loadDetail };
});
