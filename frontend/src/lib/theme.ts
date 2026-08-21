export type ThemeMode = 'dark' | 'light' | 'system';

export function getStoredTheme(): ThemeMode {
  const stored = localStorage.getItem('paypilot_theme') as ThemeMode;
  if (stored === 'dark' || stored === 'light' || stored === 'system') {
    return stored;
  }
  return 'dark';
}

export function getStoredCurrency(): string {
  return localStorage.getItem('paypilot_currency') || 'INR';
}

export function applyTheme(theme: ThemeMode): void {
  const root = document.documentElement;
  const isDark =
    theme === 'dark'
      ? true
      : theme === 'light'
      ? false
      : window.matchMedia('(prefers-color-scheme: dark)').matches;

  const resolvedTheme = isDark ? 'dark' : 'light';

  root.setAttribute('data-theme', resolvedTheme);
  document.body.setAttribute('data-theme', resolvedTheme);

  if (isDark) {
    root.classList.remove('light');
    root.classList.add('dark');
    document.body.classList.remove('light');
    document.body.classList.add('dark');
  } else {
    root.classList.remove('dark');
    root.classList.add('light');
    document.body.classList.remove('dark');
    document.body.classList.add('light');
  }

  localStorage.setItem('paypilot_theme', theme);
  window.dispatchEvent(new CustomEvent('theme-changed', { detail: { theme, resolvedTheme } }));
}

export function initTheme(): void {
  const theme = getStoredTheme();
  applyTheme(theme);

  // Listen for OS color scheme changes when theme is set to 'system'
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    if (getStoredTheme() === 'system') {
      applyTheme('system');
    }
  });
}
