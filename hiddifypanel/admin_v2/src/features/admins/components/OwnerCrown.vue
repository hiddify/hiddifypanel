<template>
  <!-- The owner's own mark: a jewelled crown, drawn here so no other admin shares it (the crown icon is the super admins') -->
  <svg class="owner-crown" viewBox="0 0 24 24" aria-hidden="true">
    <path d="M3.2 8.6 L7.6 12.2 L11.1 5.6 Q12 4.1 12.9 5.6 L16.4 12.2 L20.8 8.6 Q22 7.8 21.8 9.3 L20.2 17.4 Q20 18.6 18.8 18.6 H5.2 Q4 18.6 3.8 17.4 L2.2 9.3 Q2 7.8 3.2 8.6 Z" />
    <rect x="4.6" y="19.8" width="14.8" height="1.9" rx="0.95" />
    <circle cx="12" cy="13.6" r="1.75" class="owner-crown__gem" />
    <circle cx="7.4" cy="15.3" r="1.05" class="owner-crown__gem" />
    <circle cx="16.6" cy="15.3" r="1.05" class="owner-crown__gem" />
  </svg>
</template>

<style scoped>
.owner-crown {
  width: 1em;
  height: 1em;
  fill: currentColor;
}
.owner-crown__gem {
  fill: var(--owner-gem, rgba(255, 255, 255, 0.55));
}
</style>
