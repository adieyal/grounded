from __future__ import annotations

from importlib.resources import files

from .models import LatticeConfig
from .render_constants import CSS_FILENAME


def render_css(config: LatticeConfig) -> str:
    source = config.styles_dir / CSS_FILENAME
    if source.exists():
        return source.read_text(encoding="utf-8")
    return default_css()


def default_css() -> str:
    return files("lattice.assets").joinpath(CSS_FILENAME).read_text(encoding="utf-8")


def render_link_component() -> str:
    return """\
import { LitElement, css, html, nothing } from 'https://cdn.jsdelivr.net/npm/lit@3/+esm';

const registryElement = document.getElementById('lattice-registry');
const searchElement = document.getElementById('lattice-search-index');
const tagElement = document.getElementById('lattice-tag-index');
const latticeRegistry = registryElement ? JSON.parse(registryElement.textContent || '{}') : {};
const latticeSearchIndex = searchElement ? JSON.parse(searchElement.textContent || '[]') : [];
const latticeTagIndex = tagElement ? JSON.parse(tagElement.textContent || '{}') : {};
window.latticeRegistry = latticeRegistry;
window.latticeSearchIndex = latticeSearchIndex;
window.latticeTagIndex = latticeTagIndex;

class LatticeLink extends LitElement {
  static properties = {
    type: { type: String, reflect: true },
    latticeId: { type: String, attribute: 'lattice-id', reflect: true },
    label: { type: String, reflect: true },
    fragment: { type: String, reflect: true },
    variant: { type: String, reflect: true },
  };
  static styles = css`
    :host { --lattice-link-fg: var(--color-link); --lattice-link-bg: var(--color-chip-bg); --lattice-link-border: var(--color-chip-border); display: inline-flex; max-width: 100%; vertical-align: baseline; }
    :host([type="concept"]) { --lattice-link-fg: var(--color-concept); --lattice-link-bg: var(--color-concept-bg); --lattice-link-border: var(--color-border-tertiary); }
    :host([type="domain_object"]), :host([type="business_entity"]) { --lattice-link-fg: var(--color-entity); --lattice-link-bg: var(--color-entity-bg); --lattice-link-border: var(--color-border-tertiary); }
    :host([type="enum"]), :host([type="lifecycle_type"]), :host([type="lifecycle_value"]) { --lattice-link-fg: var(--color-text-secondary); --lattice-link-bg: var(--color-enum-bg); --lattice-link-border: var(--color-border-tertiary); }
    :host([type="tag"]) { --lattice-link-fg: var(--color-text-secondary); --lattice-link-bg: var(--color-bg-secondary); --lattice-link-border: var(--color-border-tertiary); }
    :host([type="workflow"]) { --lattice-link-fg: var(--color-concept); --lattice-link-bg: var(--color-concept-bg); --lattice-link-border: var(--color-border-tertiary); }
    :host([type="data_type"]) { --lattice-link-fg: var(--color-entity-dark); --lattice-link-bg: var(--color-type-bg); --lattice-link-border: var(--color-border-tertiary); }
    :host([type="decision"]), :host([type="business_rule"]), :host([type="guardrail"]), :host([type="schema_gap"]), :host([type="spec_type"]), :host([type="test_binding"]) { --lattice-link-fg: var(--color-text-secondary); --lattice-link-bg: var(--color-bg-secondary); --lattice-link-border: var(--color-border-tertiary); }
    a { align-items: center; background: var(--lattice-link-bg); border: var(--border-width) solid var(--lattice-link-border); border-radius: var(--radius-sm); color: var(--lattice-link-fg); display: inline-flex; font: var(--font-weight-medium) var(--font-size-xs)/1.2 var(--font-mono); max-width: 100%; padding: var(--space-2xs) var(--space-sm); text-decoration: none; }
    a:hover, a:focus { filter: saturate(1.08) brightness(0.98); color: var(--lattice-link-fg); }
    a:focus-visible { outline: 2px solid var(--lattice-link-fg); outline-offset: 2px; }
    :host([variant="text"]) a { background: transparent; border: 0; border-radius: 0; color: var(--lattice-link-fg); display: inline; font: inherit; padding: 0; text-decoration: underline; text-decoration-thickness: 0.08em; text-underline-offset: 0.18em; }
    :host([variant="plain"]) a { background: transparent; border: 0; border-radius: 0; color: var(--lattice-link-fg); display: inline; font: inherit; padding: 0; text-decoration: none; }
    :host([variant="plain"]) a:hover { text-decoration: underline; }
    :host([variant="nav"]) { display: block; min-width: 0; }
    :host([variant="nav"]) a { background: transparent; border: 0; border-radius: 0; color: inherit; display: block; font: inherit; min-width: 0; padding: 0; text-decoration: none; }
    :host([variant="card-title"]) a { background: transparent; border: 0; border-radius: 0; color: var(--lattice-link-fg); display: inline; font: var(--font-weight-medium) var(--font-size-md)/1.3 var(--font-sans); padding: 0; text-decoration: none; }
    :host([variant="card-title"]) a:hover { text-decoration: underline; }
    :host([variant="tag"]) a { background: var(--color-bg-secondary); border-color: var(--color-border-tertiary); border-radius: var(--radius-pill); color: var(--color-text-secondary); font: var(--font-weight-medium) var(--font-size-2xs)/1.2 var(--font-mono); padding: var(--space-3xs) var(--space-md); text-decoration: none; }
    :host([variant="tag"]) a:hover { background: var(--color-bg-primary); text-decoration: none; }
    :host([variant="field-type"]) a { background: var(--color-type-bg); border-color: transparent; border-radius: var(--radius-xs); color: var(--color-entity-dark); font: var(--font-weight-medium) var(--font-size-xs)/1.2 var(--font-mono); padding: var(--space-3xs) var(--space-sm); }
  `;
  render() {
    const target =
      latticeRegistry[`${this.type}:${this.latticeId}`] ||
      latticeTagIndex[this.latticeId] ||
      Object.values(latticeRegistry).find((node) => node.id === this.latticeId);
    const explicitLabel = (this.label || '').trim();
    const fragment = (this.fragment || '').trim();
    const slotLabel = (this.textContent || '').trim();
    const label = explicitLabel || slotLabel || (target ? target.label : this.latticeId);
    const href = target ? `${target.href}${fragment ? `#${fragment}` : ''}` : fragment ? `#${fragment}` : '#';
    return html`<a href=${href} part="anchor" data-lattice-type=${this.type || ''} data-lattice-id=${this.latticeId || ''}>${label}</a>`;
  }
}

class LatticeDocsApp extends LitElement {
  static styles = css`
    :host { display: block; min-height: 100vh; }
    .pd-shell { display: grid; grid-template-columns: 14.75rem minmax(0, 1fr); min-height: calc(100vh - 2.375rem); }
    @media (max-width: 760px) { .pd-shell { grid-template-columns: 1fr; } }
  `;
  render() {
    return html`
      <slot name="top"></slot>
      <div class="pd-shell"><slot name="nav"></slot><slot name="main"></slot></div>
    `;
  }
}

class LatticeTopBar extends LitElement {
  static properties = { homeHref: { type: String, attribute: 'home-href' }, label: { type: String } };
  static styles = css`
    :host { align-items: center; background: var(--color-bg-primary); border-bottom: var(--border-width) solid var(--color-border-primary); display: flex; gap: var(--space-lg); min-height: 2.375rem; padding: 0.5625rem var(--space-lg); position: sticky; top: 0; z-index: 10; }
    a { color: var(--color-text-secondary); font: var(--font-weight-medium) var(--font-size-xs)/1 var(--font-mono); letter-spacing: 0.08em; text-decoration: none; text-transform: uppercase; white-space: nowrap; }
    ::slotted(lattice-search) { flex: 1; }
    ::slotted(lattice-theme-toggle) { flex: 0 0 auto; }
    @media (max-width: 760px) { :host { align-items: stretch; flex-direction: column; } }
  `;
  render() {
    return html`<a href=${this.homeHref || 'index.html'}>${this.label || 'Project Docs'}</a><slot><lattice-search></lattice-search></slot>`;
  }
}

class LatticeSearch extends LitElement {
  static properties = { query: { type: String } };
  constructor() {
    super();
    this.query = '';
  }
  static styles = css`
    :host { align-items: center; background: var(--color-bg-secondary); border: var(--border-width) solid var(--color-border-primary); border-radius: var(--radius-md); display: flex; gap: var(--space-sm); max-width: 42rem; padding: 0.3125rem 0.625rem; position: relative; }
    .icon { color: var(--color-text-tertiary); font-size: var(--font-size-md); }
    input { background: transparent; border: 0; color: var(--color-text-primary); font: var(--font-weight-regular) var(--font-size-sm)/1.2 var(--font-sans); min-width: 0; outline: 0; width: 100%; }
    input::placeholder { color: var(--color-text-tertiary); }
    ul { background: var(--color-bg-primary); border: var(--border-width) solid var(--color-border-tertiary); border-radius: var(--radius-md); box-shadow: 0 1rem 2.5rem rgba(0, 0, 0, 0.08); display: grid; gap: var(--space-3xs); left: 0; list-style: none; margin: 0; max-height: 18rem; overflow: auto; padding: 0; position: absolute; right: 0; top: calc(100% + var(--space-xs)); z-index: 20; }
    a { color: var(--color-text-primary); display: grid; gap: var(--space-3xs); padding: var(--space-sm) var(--space-md); text-decoration: none; }
    a:hover { background: var(--color-bg-secondary); }
    span { color: var(--color-text-tertiary); font: var(--font-weight-medium) var(--font-size-xs)/1.2 var(--font-mono); }
  `;
  get results() {
    const query = this.query.trim().toLowerCase();
    if (!query) return [];
    return latticeSearchIndex.filter((item) => item.text.includes(query)).slice(0, 12);
  }
  render() {
    return html`
      <span class="icon" aria-hidden="true">/</span>
      <input type="search" placeholder="Search knowledge units..." aria-label="Search knowledge units" .value=${this.query} @input=${(event) => { this.query = event.target.value; }}>
      ${this.results.length ? html`<ul>${this.results.map((item) => html`<li><a href=${item.href}><strong>${item.name}</strong><span>${item.type} - ${item.id}</span></a></li>`)}</ul>` : nothing}
    `;
  }
}

const themeStorageKey = 'lattice-theme';
const explicitThemes = new Set(['light', 'dark']);
const storedTheme = () => {
  try {
    const theme = window.localStorage.getItem(themeStorageKey);
    return explicitThemes.has(theme) ? theme : '';
  } catch {
    return '';
  }
};
const systemTheme = () => window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';

class LatticeThemeToggle extends LitElement {
  static properties = { theme: { type: String, reflect: true } };
  constructor() {
    super();
    this.theme = storedTheme() || systemTheme();
    this._mediaQuery = null;
    this._onSystemThemeChange = () => {
      if (!storedTheme()) this.theme = systemTheme();
    };
  }
  connectedCallback() {
    super.connectedCallback();
    this.syncTheme();
    if (window.matchMedia) {
      this._mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      this._mediaQuery.addEventListener('change', this._onSystemThemeChange);
    }
  }
  disconnectedCallback() {
    if (this._mediaQuery) {
      this._mediaQuery.removeEventListener('change', this._onSystemThemeChange);
    }
    super.disconnectedCallback();
  }
  static styles = css`
    :host { display: inline-flex; }
    button { align-items: center; background: var(--color-bg-secondary); border: var(--border-width) solid var(--color-border-tertiary); border-radius: var(--radius-sm); color: var(--color-text-secondary); cursor: pointer; display: inline-flex; font: var(--font-weight-medium) var(--font-size-xs)/1.2 var(--font-mono); gap: var(--space-xs); min-height: 1.75rem; padding: var(--space-2xs) var(--space-sm); white-space: nowrap; }
    button:hover { border-color: var(--color-border-primary); color: var(--color-text-primary); }
    button:focus-visible { outline: 2px solid var(--color-link); outline-offset: 2px; }
    .mark { border: var(--border-width) solid var(--color-text-tertiary); border-radius: 999px; display: inline-block; height: 0.75rem; position: relative; width: 0.75rem; }
    :host([theme="light"]) .mark { background: var(--color-text-secondary); box-shadow: 0 0 0 0.125rem var(--color-bg-secondary) inset; }
    :host([theme="dark"]) .mark { background: transparent; box-shadow: inset -0.22rem -0.12rem 0 0 var(--color-text-secondary); }
    @media (max-width: 760px) { button { justify-content: center; width: 100%; } }
  `;
  syncTheme() {
    const theme = storedTheme();
    if (theme) {
      document.documentElement.dataset.theme = theme;
      this.theme = theme;
      return;
    }
    document.documentElement.removeAttribute('data-theme');
    this.theme = systemTheme();
  }
  setTheme(theme) {
    document.documentElement.dataset.theme = theme;
    try {
      window.localStorage.setItem(themeStorageKey, theme);
    } catch {}
    this.theme = theme;
  }
  toggleTheme() {
    this.setTheme(this.theme === 'dark' ? 'light' : 'dark');
  }
  render() {
    const next = this.theme === 'dark' ? 'light' : 'dark';
    return html`<button type="button" aria-label=${`Switch to ${next} theme`} title=${`Switch to ${next} theme`} @click=${this.toggleTheme}><span class="mark" aria-hidden="true"></span><span>${this.theme === 'dark' ? 'Dark' : 'Light'}</span></button>`;
  }
}

class LatticeSidebar extends LitElement {
  static styles = css`
    :host { background: var(--color-bg-secondary); border-right: var(--border-width) solid var(--color-border-primary); display: block; height: calc(100vh - 2.375rem); overflow-y: auto; padding: var(--space-md) 0; position: sticky; top: 2.375rem; }
    @media (max-width: 760px) { :host { border-bottom: var(--border-width) solid var(--color-border-primary); border-right: 0; height: auto; max-height: 14rem; position: static; } }
  `;
  render() { return html`<slot></slot>`; }
}

class LatticeNavGroup extends LitElement {
  static styles = css`
    :host { display: block; margin-bottom: var(--space-lg); }
    h2 { color: var(--color-text-tertiary); font: var(--font-weight-medium) var(--font-size-2xs)/1.2 var(--font-mono); letter-spacing: 0.15em; margin: 0; padding: 0 var(--space-md) var(--space-xs); text-transform: uppercase; }
  `;
  render() { return html`<h2><slot name="label"></slot></h2><slot></slot>`; }
}

class LatticeNavItem extends LitElement {
  static properties = { tone: { type: String, reflect: true }, active: { type: Boolean, reflect: true } };
  static styles = css`
    :host { align-items: flex-start; border-left: 2px solid transparent; color: var(--color-text-secondary); display: flex; font-size: var(--font-size-sm); gap: var(--space-sm); line-height: 1.35; padding: 0.3125rem var(--space-md); }
    :host(:hover), :host([active]) { background: var(--color-bg-primary); color: var(--color-text-primary); }
    :host([active]) { font-weight: var(--font-weight-medium); }
    :host([active][tone="ent"]) { border-left-color: var(--color-entity); }
    :host([active][tone="con"]) { border-left-color: var(--color-concept); }
    :host([active][tone="enu"]) { border-left-color: var(--color-enum); }
    .dot { background: var(--color-text-tertiary); border-radius: 999px; flex: 0 0 auto; height: 0.375rem; margin-top: 0.3125rem; width: 0.375rem; }
    :host([tone="ent"]) .dot { background: var(--color-entity); }
    :host([tone="con"]) .dot { background: var(--color-brand-primary); }
    :host([tone="enu"]) .dot { background: var(--color-enum); }
  `;
  render() { return html`<span class="dot" aria-hidden="true"></span><slot></slot>`; }
}

class LatticeMain extends LitElement {
  static styles = css`:host { display: block; min-width: 0; overflow-x: auto; }`;
  render() { return html`<slot></slot>`; }
}

class LatticePageHero extends LitElement {
  static styles = css`
    :host { border-bottom: var(--border-width) solid var(--color-border-tertiary); display: block; padding: 1.375rem var(--space-2xl) 1.125rem; }
    .eyebrow { color: var(--color-entity-dark); font: var(--font-weight-medium) var(--font-size-2xs)/1.2 var(--font-mono); letter-spacing: 0.2em; margin-bottom: var(--space-xs); text-transform: uppercase; }
    h1 { font: var(--font-weight-medium) var(--font-size-title)/1 var(--font-serif); margin: 0 0 var(--space-sm); }
    p { color: var(--color-text-secondary); font-size: var(--font-size-md); line-height: 1.6; margin: 0 0 var(--space-md); max-width: 36.25rem; }
    @media (max-width: 760px) { :host { padding-inline: var(--space-lg); } }
  `;
  render() {
    return html`<div class="eyebrow"><slot name="eyebrow"></slot></div><h1><slot name="title"></slot></h1><p><slot name="description"></slot></p><slot name="actions"></slot>`;
  }
}

class LatticeDocHeader extends LitElement {
  static styles = css`
    :host { border-bottom: var(--border-width) solid var(--color-border-tertiary); display: block; padding: 1.5rem var(--space-2xl) 1.25rem; }
    .eyebrow { align-items: center; display: flex; gap: var(--space-sm); margin-bottom: var(--space-sm); }
    .type-badge { background: var(--color-chip-bg); border: var(--border-width) solid var(--color-chip-border); border-radius: 999px; color: var(--color-text-secondary); display: inline-flex; font: var(--font-weight-medium) var(--font-size-2xs)/1.2 var(--font-mono); letter-spacing: 0.12em; padding: var(--space-2xs) var(--space-sm); text-transform: uppercase; }
    h1 { color: var(--color-text-primary); font: var(--font-weight-medium) var(--font-size-title)/1 var(--font-serif); margin: 0 0 var(--space-md); }
    .lead { color: var(--color-text-secondary); font-size: var(--font-size-md); line-height: 1.65; margin: 0; max-width: 46rem; }
    .actions { display: flex; flex-wrap: wrap; gap: var(--space-sm); margin-top: var(--space-md); }
    @media (max-width: 760px) { :host { padding-inline: var(--space-lg); } }
  `;
  render() {
    return html`
      <div class="eyebrow"><span class="type-badge"><slot name="eyebrow"><slot name="type"></slot></slot></span></div>
      <h1><slot name="title"></slot></h1>
      <p class="lead"><slot name="lead"><slot name="description"></slot></slot></p>
      <div class="actions"><slot name="actions"></slot></div>
    `;
  }
}

class LatticeCopyId extends LitElement {
  static properties = { value: { type: String }, copied: { type: Boolean } };
  constructor() {
    super();
    this.value = '';
    this.copied = false;
  }
  static styles = css`
    button { align-items: center; background: var(--color-bg-secondary); border: var(--border-width) solid var(--color-border-tertiary); border-radius: var(--radius-sm); color: var(--color-text-tertiary); cursor: pointer; display: inline-flex; font: var(--font-weight-medium) var(--font-size-xs)/1.2 var(--font-mono); gap: var(--space-xs); padding: var(--space-2xs) var(--space-sm); }
    button:hover { color: var(--color-text-secondary); }
  `;
  async copy() {
    if (!this.value) return;
    try {
      await navigator.clipboard.writeText(this.value);
      this.copied = true;
      window.setTimeout(() => { this.copied = false; }, 1100);
    } catch {
      window.prompt('Copy ID', this.value);
    }
  }
  render() { return html`<button type="button" aria-label=${`Copy item ID ${this.value}`} @click=${this.copy}>${this.copied ? 'Copied' : 'Copy ID'}</button>`; }
}

class LatticeSectionHeading extends LitElement {
  static styles = css`
    :host { align-items: center; color: var(--color-text-tertiary); display: flex; font: var(--font-weight-medium) var(--font-size-2xs)/1.2 var(--font-mono); gap: var(--space-sm); letter-spacing: 0.15em; margin-bottom: 0.625rem; text-transform: uppercase; }
    :host([divider])::after { background: var(--color-border-tertiary); content: ""; flex: 1; height: var(--border-width); }
  `;
  render() { return html`<slot></slot>`; }
}

class LatticeIndexPage extends LitElement { render() { return html`<slot></slot>`; } }
class LatticeBackgroundPage extends LitElement { render() { return html`<slot></slot>`; } }
class LatticeTagPage extends LitElement { render() { return html`<slot></slot>`; } }
class LatticeUnitPage extends LitElement {
  static styles = css`
    .unit-layout { display: block; }
    article { max-width: 64rem; padding: 1.25rem var(--space-2xl) 2rem; }
    @media (max-width: 760px) { article { padding-inline: var(--space-lg); } }
  `;
  render() {
    return html`<slot name="hero"></slot><div class="unit-layout"><article><slot name="fields"></slot><slot name="before-context"></slot><slot name="context"></slot><slot name="links"></slot><slot name="raw"></slot></article></div>`;
  }
}

const unitSlots = html`
  <slot name="hero" slot="hero"></slot>
  <slot name="fields" slot="fields"></slot>
  <slot name="before-context" slot="before-context"></slot>
  <slot name="context" slot="context"></slot>
  <slot name="links" slot="links"></slot>
  <slot name="raw" slot="raw"></slot>
`;
class LatticeBusinessEntityPage extends LitElement { render() { return html`<lattice-unit-page>${unitSlots}</lattice-unit-page>`; } }
class LatticeDomainObjectPage extends LitElement { render() { return html`<lattice-unit-page>${unitSlots}</lattice-unit-page>`; } }
class LatticeEnumPage extends LitElement { render() { return html`<lattice-unit-page>${unitSlots}</lattice-unit-page>`; } }
class LatticeLifecycleTypePage extends LitElement { render() { return html`<lattice-unit-page>${unitSlots}</lattice-unit-page>`; } }

class LatticeFieldTable extends LitElement { static styles = css`:host { display: block; }`; render() { return html`<slot></slot>`; } }
class LatticeConceptSection extends LitElement { static styles = css`:host { display: grid; gap: 0.4375rem; margin-bottom: var(--space-xl); }`; render() { return html`<slot></slot>`; } }
class LatticeConceptCard extends LitElement { static styles = css`:host { background: var(--color-bg-secondary); border: var(--border-width) solid var(--color-border-tertiary); border-radius: var(--radius-md); display: block; padding: var(--space-xl); }`; render() { return html`<slot></slot>`; } }
class LatticeSection extends LitElement {
  static properties = { label: { type: String } };
  static styles = css`
    :host { border-top: var(--border-width) solid var(--color-border-tertiary); display: block; margin-top: var(--space-xl); padding-top: var(--space-xl); }
    .label { color: var(--color-text-tertiary); font: var(--font-weight-medium) var(--font-size-2xs)/1.2 var(--font-mono); letter-spacing: 0.14em; margin-bottom: var(--space-sm); text-transform: uppercase; }
    .body { color: var(--color-text-secondary); font-size: var(--font-size-md); line-height: 1.65; }
  `;
  render() { return html`<section><div class="label"><slot name="label">${this.label || ''}</slot></div><div class="body"><slot></slot></div></section>`; }
}
class LatticePillLinkList extends LitElement {
  static properties = { label: { type: String } };
  static styles = css`
    :host { background: var(--color-bg-secondary); border: var(--border-width) solid var(--color-border-tertiary); border-radius: var(--radius-md); display: block; padding: var(--space-md); }
    .label { color: var(--color-text-tertiary); font: var(--font-weight-medium) var(--font-size-2xs)/1.2 var(--font-mono); letter-spacing: 0.12em; margin-bottom: var(--space-sm); text-transform: uppercase; }
    .links { display: flex; flex-wrap: wrap; gap: var(--space-xs); }
  `;
  render() { return html`<div class="label"><slot name="label">${this.label || ''}</slot></div><div class="links"><slot></slot></div>`; }
}
class LatticeCompactList extends LitElement { static styles = css`:host { display: grid; gap: 0; }`; render() { return html`<slot></slot>`; } }
class LatticeCompactItem extends LitElement {
  static styles = css`
    :host { border-bottom: var(--border-width) solid var(--color-border-tertiary); display: block; padding: 0.5625rem 0; }
    :host(:first-child) { padding-top: 0; }
    :host(:last-child) { border-bottom: 0; padding-bottom: 0; }
    .name { color: var(--color-text-primary); font: var(--font-weight-medium) var(--font-size-sm)/1.35 var(--font-sans); margin: 0 0 var(--space-3xs); }
    .description { color: var(--color-text-secondary); font-size: var(--font-size-xs); line-height: 1.5; margin: 0; }
    ::slotted([slot="description"]) { margin: 0; }
  `;
  render() { return html`<div class="name"><slot name="name"></slot></div><div class="description"><slot name="description"></slot></div>`; }
}
class LatticeDetailList extends LitElement {
  static styles = css`
    :host { border: var(--border-width) solid var(--color-border-tertiary); border-radius: var(--radius-md); display: block; overflow: hidden; }
  `;
  render() { return html`<slot></slot>`; }
}
class LatticeDetailRow extends LitElement {
  static styles = css`
    :host { background: var(--color-bg-primary); border-bottom: var(--border-width) solid var(--color-border-tertiary); display: grid; grid-template-columns: minmax(12rem, 16rem) minmax(0, 1fr) minmax(10rem, 14rem); }
    :host(:last-child) { border-bottom: 0; }
    :host(:hover) { background: var(--color-bg-secondary); }
    .main, .examples, .related { padding: var(--space-md); }
    .main, .examples { border-right: var(--border-width) solid var(--color-border-tertiary); }
    .title-row { align-items: center; display: flex; gap: var(--space-sm); margin-bottom: var(--space-sm); }
    .icon { align-items: center; background: var(--color-entity-bg); border-radius: var(--radius-md); color: var(--color-entity-dark); display: inline-flex; flex: 0 0 auto; height: 1.625rem; justify-content: center; width: 1.625rem; }
    .title { color: var(--color-text-primary); font: var(--font-weight-medium) var(--font-size-sm)/1.35 var(--font-sans); }
    .description { color: var(--color-text-secondary); font-size: var(--font-size-sm); line-height: 1.55; }
    .column-label { color: var(--color-text-tertiary); font: var(--font-weight-medium) var(--font-size-2xs)/1.2 var(--font-mono); letter-spacing: 0.1em; margin-bottom: var(--space-xs); text-transform: uppercase; }
    .examples, .related { color: var(--color-text-secondary); font-size: var(--font-size-xs); line-height: 1.55; }
    ::slotted([slot="description"]), ::slotted([slot="examples"]), ::slotted([slot="related"]) { margin: 0; }
    @media (max-width: 860px) {
      :host { grid-template-columns: 1fr; }
      .main, .examples { border-bottom: var(--border-width) solid var(--color-border-tertiary); border-right: 0; }
    }
  `;
  render() {
    return html`
      <div class="main">
        <div class="title-row"><span class="icon"><slot name="icon">-</slot></span><div class="title"><slot name="title"></slot></div></div>
        <div class="description"><slot name="description"></slot></div>
      </div>
      <div class="examples"><div class="column-label">Examples</div><slot name="examples"></slot></div>
      <div class="related"><div class="column-label">Related</div><slot name="related"></slot></div>
    `;
  }
}
class LatticeLinksPanel extends LitElement { static styles = css`:host { display: block; margin-bottom: var(--space-xl); }`; render() { return html`<slot></slot>`; } }
class LatticeRawJson extends LitElement { static styles = css`:host { display: block; }`; render() { return html`<slot></slot>`; } }
class LatticeUnitSection extends LitElement { static styles = css`:host { border-bottom: var(--border-width) solid var(--color-border-tertiary); display: block; padding: var(--space-lg) var(--space-xl); }`; render() { return html`<slot></slot>`; } }
class LatticeUnitCard extends LitElement { static styles = css`:host { background: var(--color-bg-secondary); border: var(--border-width) solid var(--color-border-tertiary); border-radius: var(--radius-md); display: flex; flex-direction: column; min-height: 6rem; padding: var(--space-xl); } :host(:hover) { border-color: var(--color-border-primary); }`; render() { return html`<slot></slot>`; } }

const define = (name, component) => {
  if (!customElements.get(name)) customElements.define(name, component);
};
define('lattice-link', LatticeLink);
define('lattice-docs-app', LatticeDocsApp);
define('lattice-top-bar', LatticeTopBar);
define('lattice-search', LatticeSearch);
define('lattice-theme-toggle', LatticeThemeToggle);
define('lattice-sidebar', LatticeSidebar);
define('lattice-nav-group', LatticeNavGroup);
define('lattice-nav-item', LatticeNavItem);
define('lattice-main', LatticeMain);
define('lattice-page-hero', LatticePageHero);
define('lattice-doc-header', LatticeDocHeader);
define('lattice-copy-id', LatticeCopyId);
define('lattice-section-heading', LatticeSectionHeading);
define('lattice-index-page', LatticeIndexPage);
define('lattice-background-page', LatticeBackgroundPage);
define('lattice-tag-page', LatticeTagPage);
define('lattice-unit-page', LatticeUnitPage);
define('lattice-business-entity-page', LatticeBusinessEntityPage);
define('lattice-domain-object-page', LatticeDomainObjectPage);
define('lattice-enum-page', LatticeEnumPage);
define('lattice-lifecycle-type-page', LatticeLifecycleTypePage);
define('lattice-field-table', LatticeFieldTable);
define('lattice-concept-section', LatticeConceptSection);
define('lattice-concept-card', LatticeConceptCard);
define('lattice-section', LatticeSection);
define('lattice-pill-link-list', LatticePillLinkList);
define('lattice-compact-list', LatticeCompactList);
define('lattice-compact-item', LatticeCompactItem);
define('lattice-detail-list', LatticeDetailList);
define('lattice-detail-row', LatticeDetailRow);
define('lattice-links-panel', LatticeLinksPanel);
define('lattice-raw-json', LatticeRawJson);
define('lattice-unit-section', LatticeUnitSection);
define('lattice-unit-card', LatticeUnitCard);
"""
