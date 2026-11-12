<script setup lang="ts">
defineProps<{ message: string }>();
defineEmits<{ retry: [] }>();
</script>

<template>
  <div class="error" role="alert">
    <span>{{ message }}</span>
    <button class="btn btn--small" type="button" @click="$emit('retry')">重试</button>
  </div>
</template>
