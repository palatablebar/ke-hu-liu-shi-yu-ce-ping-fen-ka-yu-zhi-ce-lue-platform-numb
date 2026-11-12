<script setup lang="ts">
withDefaults(defineProps<{ label: string; tone?: string }>(), { tone: 'seal--neutral' });
</script>

<template>
  <span class="seal" :class="tone">{{ label }}</span>
</template>
