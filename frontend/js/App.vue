<template>
  <!-- Main application component representing the entry point for the Vue app -->
  <main class="app-shell">
    <section class="hero">
      <p class="eyebrow">Django + Vue</p>
      <h1>QUICK START</h1>
      <p class="lede">
        A pragmatic default for shipping web apps fast with Django 6, Vue 3, and modern tooling. Delivers a pre-validated, connected starter with minimal configuration overhead—a proven path to launch without complex infrastructure upfront.
      </p>
      <div class="actions">
        <a
          href="https://github.com/mikebz/djangovue"
          target="_blank"
          rel="noopener noreferrer"
          class="primary-action"
          >GitHub Repository</a
        >
        <a href="https://vuejs.org/" target="_blank" rel="noopener noreferrer"
          >Vue docs</a
        >
        <a href="https://vite.dev/" target="_blank" rel="noopener noreferrer"
          >Vite docs</a
        >
      </div>
    </section>
  </main>
</template>

<style scoped>
:global(body) {
  margin: 0;
  min-height: 100vh;
  background:
    radial-gradient(circle at top, rgba(82, 183, 136, 0.16), transparent 42%),
    linear-gradient(180deg, #f7fafc 0%, #edf4f7 100%);
  color: #17313d;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
    "Segoe UI", sans-serif;
}

.app-shell {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 2rem;
}

.hero {
  width: min(100%, 44rem);
  padding: clamp(2rem, 4vw, 4rem);
  border: 1px solid rgba(23, 49, 61, 0.08);
  border-radius: 1.5rem;
  background: rgba(255, 255, 255, 0.78);
  box-shadow: 0 20px 60px rgba(23, 49, 61, 0.12);
  backdrop-filter: blur(14px);
}

.eyebrow {
  margin: 0 0 0.75rem;
  font-size: 0.85rem;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: #4b7a86;
}

h1 {
  margin: 0;
  font-size: clamp(2.5rem, 7vw, 4.5rem);
  line-height: 0.95;
  letter-spacing: -0.04em;
  text-transform: uppercase;
}

.lede {
  margin: 1.25rem 0 0;
  max-width: 34rem;
  font-size: 1.05rem;
  line-height: 1.65;
  color: rgba(23, 49, 61, 0.82);
}

.actions {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-top: 2rem;
}

.actions a {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 10rem;
  padding: 0.85rem 1.1rem;
  border-radius: 999px;
  text-decoration: none;
  font-weight: 700;
  color: #17313d;
  background: #d8f0e6;
  transition: transform 0.18s ease, box-shadow 0.18s ease, background-color 0.18s ease;
}

.actions a.primary-action {
  background: #17313d;
  color: #ffffff;
}

.actions a.primary-action:hover {
  background: #0f6779;
}

.actions a:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 24px rgba(23, 49, 61, 0.14);
}

.actions a:focus-visible {
  outline: 3px solid #0f6779;
  outline-offset: 2px;
  transform: translateY(-1px);
  box-shadow: 0 10px 24px rgba(23, 49, 61, 0.14);
}
</style>
