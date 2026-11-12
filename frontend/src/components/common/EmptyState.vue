<script setup lang="ts">
defineProps<{ title: string; text?: string }>();
</script>

<template>
  <div class="empty">
    <p class="empty__title">{{ title }}</p>
    <p v-if="text" class="small muted">{{ text }}</p>
    <slot />
  </div>
</template>
