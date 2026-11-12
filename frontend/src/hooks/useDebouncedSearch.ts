import { onBeforeUnmount, ref, watch, type Ref } from 'vue';

export function useDebouncedSearch(initial = '', delay = 260): {
  keyword: Ref<string>;
  debounced: Ref<string>;
  reset: () => void;
} {
  const keyword = ref(initial);
  const debounced = ref(initial);
  let timer: ReturnType<typeof setTimeout> | null = null;

  watch(keyword, (value) => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => {
      debounced.value = value.trim();
    }, delay);
  });

  onBeforeUnmount(() => {
    if (timer) clearTimeout(timer);
  });

  function reset(): void {
    keyword.value = '';
    debounced.value = '';
  }

  return { keyword, debounced, reset };
}
