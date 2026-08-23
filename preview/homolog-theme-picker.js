(() => {
  'use strict';

  const host = window.location.hostname.toLowerCase();
  const isHomologation =
    host === 'localhost' ||
    host === '127.0.0.1' ||
    host.endsWith('.onrender.com') ||
    host.endsWith('.vercel.app') ||
    host.includes('homolog');

  if (!isHomologation) return;

  const PICKER_ID = 'acs-homolog-skin-picker';
  const STORAGE_KEY = 'acs.homolog.workspace-skin';
  const SKINS = [
    { id: 'black', label: 'Preto', color: '#000000', bg: '#000000', panel: '#090909', line: '#2b2b2b', text: '#f5f5f5', muted: '#a3a3a3', accent: '#e4e4e7', accent2: '#71717a' },
    { id: 'yellow', label: 'Amarelo', color: '#ffd84d', bg: '#151000', panel: '#211a03', line: '#5f4e10', text: '#fff9d7', muted: '#d8c782', accent: '#ffd84d', accent2: '#ffb31a' },
    { id: 'red', label: 'Vermelho', color: '#ff526b', bg: '#150407', panel: '#22080d', line: '#66202d', text: '#fff0f3', muted: '#d8a2ad', accent: '#ff526b', accent2: '#d91f3e' },
    { id: 'blue', label: 'Azul', color: '#4d94ff', bg: '#030b18', panel: '#081427', line: '#244b78', text: '#edf6ff', muted: '#9cb6d3', accent: '#4d94ff', accent2: '#2f68e8' },
    { id: 'green', label: 'Verde', color: '#42d99c', bg: '#03110c', panel: '#071d15', line: '#245f46', text: '#effff8', muted: '#9bc9b5', accent: '#42d99c', accent2: '#1fb879' },
    { id: 'white', label: 'Branco', color: '#ffffff', bg: '#f5f7fa', panel: '#ffffff', line: '#cfd6df', text: '#111827', muted: '#667085', accent: '#111827', accent2: '#475467' },
  ];

  const style = document.createElement('style');
  style.textContent = `
    #${PICKER_ID}{position:fixed;top:18px;right:18px;z-index:2147483000;display:flex;align-items:center;gap:8px;padding:7px;border:1px solid var(--line);border-radius:16px;background:color-mix(in srgb,var(--panel) 94%,transparent);box-shadow:0 14px 38px #0005;backdrop-filter:blur(14px)}
    #${PICKER_ID}.is-collapsed{gap:0;padding:4px}
    #${PICKER_ID} .swatches{display:flex;align-items:center;gap:7px;max-width:260px;opacity:1;overflow:hidden;transition:max-width .2s ease,opacity .14s ease,gap .2s ease}
    #${PICKER_ID}.is-collapsed .swatches{max-width:0;gap:0;opacity:0;pointer-events:none}
    #${PICKER_ID} .swatch{--swatch:#000;width:31px;height:31px;padding:0;flex:0 0 31px;border:2px solid #ffffff55;border-radius:50%;background:var(--swatch);cursor:pointer;box-shadow:inset 0 0 0 2px #ffffff18}
    #${PICKER_ID} .swatch[aria-pressed="true"]{border-color:var(--text);box-shadow:0 0 0 3px color-mix(in srgb,var(--accent) 28%,transparent)}
    #${PICKER_ID} .toggle{width:42px;height:42px;padding:0;flex:0 0 42px;display:grid;place-items:center;border:1px solid var(--line);border-radius:13px;background:linear-gradient(135deg,var(--panel),color-mix(in srgb,var(--accent) 28%,var(--panel)));color:var(--text);font:900 22px/1 system-ui;cursor:pointer}
    @media(max-width:720px){#${PICKER_ID}{top:8px;right:8px}#${PICKER_ID} .swatch{width:25px;height:25px;flex-basis:25px}#${PICKER_ID} .toggle{width:36px;height:36px;flex-basis:36px}}
  `;
  document.head.appendChild(style);

  const picker = document.createElement('div');
  picker.id = PICKER_ID;
  picker.className = 'is-collapsed';
  picker.innerHTML = `<div class="swatches" role="group" aria-label="Escolha uma cor">${SKINS.map(s => `<button type="button" class="swatch" data-skin="${s.id}" aria-label="Skin ${s.label}" aria-pressed="false" style="--swatch:${s.color}"></button>`).join('')}</div><button type="button" class="toggle" aria-label="Mostrar seletor de cores" aria-expanded="false">‹</button>`;
  document.body.appendChild(picker);

  const toggle = picker.querySelector('.toggle');
  const buttons = [...picker.querySelectorAll('.swatch')];

  const setCollapsed = collapsed => {
    picker.classList.toggle('is-collapsed', collapsed);
    buttons.forEach(button => { button.tabIndex = collapsed ? -1 : 0; });
    toggle.textContent = collapsed ? '‹' : '›';
    toggle.setAttribute('aria-expanded', String(!collapsed));
    toggle.setAttribute('aria-label', collapsed ? 'Mostrar seletor de cores' : 'Esconder seletor de cores');
  };

  const applySkin = id => {
    const skin = SKINS.find(item => item.id === id) || SKINS[0];
    const root = document.documentElement;
    root.dataset.workspaceSkin = skin.id;
    root.style.setProperty('--bg', skin.bg);
    root.style.setProperty('--panel', skin.panel);
    root.style.setProperty('--line', skin.line);
    root.style.setProperty('--text', skin.text);
    root.style.setProperty('--muted', skin.muted);
    root.style.setProperty('--accent', skin.accent);
    root.style.setProperty('--accent2', skin.accent2);
    localStorage.setItem(STORAGE_KEY, skin.id);
    buttons.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.skin === skin.id)));
  };

  const saved = localStorage.getItem(STORAGE_KEY);
  applySkin(SKINS.some(skin => skin.id === saved) ? saved : 'black');
  setCollapsed(true);

  toggle.addEventListener('click', event => {
    event.stopPropagation();
    setCollapsed(!picker.classList.contains('is-collapsed'));
  });
  buttons.forEach(button => button.addEventListener('click', event => {
    event.stopPropagation();
    applySkin(button.dataset.skin);
  }));
  document.addEventListener('click', event => {
    if (!picker.contains(event.target)) setCollapsed(true);
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') setCollapsed(true);
  });
})();
