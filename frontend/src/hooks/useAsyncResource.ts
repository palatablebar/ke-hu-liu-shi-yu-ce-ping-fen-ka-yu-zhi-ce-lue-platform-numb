import { ref, type Ref } from 'vue';

interface AsyncResource<T> {
  data: Ref<T | null>;
  loading: Ref<boolean>;
  error: Ref<string>;
  run: (task: () => Promise<T>) => Promise<T | null>;
  reset: () => void;
}

export function useAsyncResource<T>(initial: T | null = null): AsyncResource<T> {
  const data = ref<T | null>(initial) as Ref<T | null>;
  const loading = ref(false);
  const error = ref('');

  async function run(task: () => Promise<T>): Promise<T | null> {
    loading.value = true;
    error.value = '';
    try {
      const result = await task();
      data.value = result;
      return result;
    } catch (err) {
      error.value = err instanceof Error ? err.message : '请求失败';
      return null;
    } finally {
      loading.value = false;
    }
  }

  function reset(): void {
    data.value = initial;
    error.value = '';
    loading.value = false;
  }

  return { data, loading, error, run, reset };
}
