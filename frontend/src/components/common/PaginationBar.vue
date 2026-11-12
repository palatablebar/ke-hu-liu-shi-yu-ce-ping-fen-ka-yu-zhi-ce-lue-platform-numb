<script setup lang="ts">
const props = defineProps<{ page: number; pages: number; total: number; pageSize: number }>();
const emit = defineEmits<{ change: [page: number] }>();

function go(delta: number) {
  const next = props.page + delta;
  if (next >= 1 && next <= props.pages) emit('change', next);
}
</script>

<template>
  <div class="pager">
    <span>共 {{ total }} 家 · 第 {{ page }} / {{ pages }} 页 · 每页 {{ pageSize }}</span>
    <div class="pager__buttons">
      <button class="btn btn--small" type="button" :disabled="page <= 1" @click="go(-1)">上一页</button>
      <button class="btn btn--small" type="button" :disabled="page >= pages" @click="go(1)">下一页</button>
    </div>
  </div>
</template>
