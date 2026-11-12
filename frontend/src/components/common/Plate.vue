<script setup lang="ts">
defineProps<{ title?: string; kicker?: string; hint?: string }>();
</script>

<template>
  <section class="plate">
    <header v-if="title || $slots.actions" class="plate__head">
      <div>
        <p v-if="kicker" class="eyebrow">{{ kicker }}</p>
        <h2 v-if="title" class="plate__title">{{ title }}</h2>
        <p v-if="hint" class="plate__hint">{{ hint }}</p>
      </div>
      <div class="row">
        <slot name="actions" />
      </div>
    </header>
    <slot />
  </section>
</template>
