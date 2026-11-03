#!/data/data/com.termux/files/usr/bin/env python3
"""
Library:        notes_site_exporter.py
Family:         Notes / Static Site Generator
Description:    Exports categorized notes into an isomorphic, dark-themed, search-engine-
                optimized web manual and taxonomy site:
                root/ (notes/)
                ├── index.html                                (Master Portal & Category Matrix)
                ├── sitemap.html                              (Interactive HTML Sitemap)
                ├── sitemap.xml                               (W3C Standard XML Sitemap)
                ├── robots.txt                                (Crawler Directives)
                └── <category_slug>/
                    ├── index.html                            (Category Feed & Instant Filter)
                    ├── feed.html                             (Feed Alias)
                    └── <note_slug>/
                        ├── index.html                        (Dedicated Note Reader & Viewer)
                        └── <note_slug>.md                    (Collocated Raw Markdown File)
                Enforces Policy §8.1 Tri-Color (#05070B, #0B0F17, #DE2626), code-manual-builder,
                W3C XML/HTML sitemap autogen, Schema.org JSON-LD, Open Graph, Twitter Cards,
                and comprehensive ARIA accessibility.
Version:        1.1.0
Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Date:           2026-11-03
RELATIONAL_ID:  8f4b239c-5e21-4d9f-ba10-0a2b3c4d5e6f
"""

from __future__ import annotations

import html
import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import lib_md_to_html as md_engine
from notes_mfdb_engine import slugify_text


# ── Inline Dark Theme CSS (Zero CSS Drop / file:/// Immune) ──────────────────
SITE_CSS: str = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --bg-canvas: #05070B;
  --bg-surface: #0B0F17;
  --bg-elevated: #111827;
  --bg-code: #04060A;
  --border-color: #1E293B;
  --border-subtle: #151D2C;
  --accent-red: #DE2626;
  --accent-hover: #EF4444;
  --text-main: #F1F5F9;
  --text-muted: #94A3B8;
  --text-dim: #64748B;
  --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --font-mono: ui-monospace, SFMono-Regular, "Roboto Mono", Menlo, Consolas, monospace;
}
html { font-size: 15px; background: var(--bg-canvas); color: var(--text-main); font-family: var(--font-sans); line-height: 1.6; }
body { min-height: 100vh; display: flex; flex-direction: column; }
a { color: var(--text-main); text-decoration: none; transition: color 0.15s ease; }
a:hover { color: var(--accent-red); }

/* Accessible Skip Link */
.skip-link {
  position: absolute;
  top: -40px;
  left: 0.5rem;
  background: var(--accent-red);
  color: #fff;
  padding: 0.5rem 1rem;
  z-index: 999;
  font-weight: 700;
  border-radius: 0 0 4px 4px;
  transition: top 0.2s ease;
}
.skip-link:focus { top: 0; }

/* Header */
.site-header {
  height: 44px;
  background: rgba(11, 15, 23, 0.94);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--border-color);
  position: sticky;
  top: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1rem;
}
.header-left, .header-right { display: flex; align-items: center; gap: 0.75rem; }
.menu-btn {
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-main);
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}
.menu-btn:hover, .menu-btn:focus { border-color: var(--accent-red); color: var(--accent-red); outline: none; }
.brand-link { font-weight: 700; font-size: 0.95rem; display: flex; align-items: center; gap: 0.4rem; }
.brand-badge {
  background: var(--accent-red);
  color: #fff;
  font-size: 0.65rem;
  font-weight: 800;
  padding: 0.1rem 0.35rem;
  border-radius: 3px;
  letter-spacing: 0.5px;
}
.header-link { font-size: 0.8rem; color: var(--text-muted); display: inline-flex; align-items: center; gap: 0.2rem; }
.header-link:hover { color: var(--accent-red); }

/* Container & Layout */
.container { max-width: 1040px; margin: 0 auto; width: 100%; padding: 1rem 1rem 3rem; flex: 1; }
.page-bar {
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-left: 3px solid var(--accent-red);
  border-radius: 4px;
  padding: 0.65rem 0.85rem;
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.breadcrumbs { font-size: 0.8rem; color: var(--text-muted); display: flex; align-items: center; gap: 0.35rem; }
.breadcrumbs span.sep { color: var(--text-dim); }
.breadcrumbs span.current { color: var(--text-main); font-weight: 600; }
.telemetry-strip { font-size: 0.75rem; color: var(--text-dim); display: flex; align-items: center; gap: 0.8rem; }

/* Tag Pills */
.tags-row { display: flex; flex-wrap: wrap; gap: 0.35rem; margin: 0.5rem 0 1rem; }
.tag-pill {
  background: rgba(222, 38, 38, 0.12);
  border: 1px solid rgba(222, 38, 38, 0.3);
  color: #F87171;
  font-size: 0.75rem;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  font-family: var(--font-mono);
  font-weight: 500;
}
.tag-pill:hover { background: rgba(222, 38, 38, 0.25); border-color: var(--accent-red); color: #fff; }

/* Article Card */
.article-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
}
.article-title { font-size: 1.8rem; font-weight: 800; line-height: 1.25; margin-bottom: 0.5rem; color: #fff; }
.action-strip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 0.75rem;
  margin-bottom: 1.25rem;
  font-size: 0.8rem;
}
.action-btn {
  background: var(--bg-elevated);
  border: 1px solid var(--border-color);
  color: var(--text-muted);
  padding: 0.25rem 0.65rem;
  border-radius: 4px;
  font-size: 0.75rem;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}
.action-btn:hover, .action-btn:focus { border-color: var(--accent-red); color: var(--text-main); outline: none; }

/* Typography & Content within .bejson-cms-article */
.bejson-cms-article { line-height: 1.7; font-size: 0.95rem; }
.bejson-cms-article h1, .bejson-cms-article h2, .bejson-cms-article h3, .bejson-cms-article h4 {
  color: #fff;
  margin: 1.5rem 0 0.6rem;
  font-weight: 700;
  line-height: 1.3;
}
.bejson-cms-article h2 { font-size: 1.35rem; border-bottom: 1px solid var(--border-subtle); padding-bottom: 0.3rem; }
.bejson-cms-article h3 { font-size: 1.15rem; }
.bejson-cms-article p { margin-bottom: 0.9rem; }
.bejson-cms-article ul, .bejson-cms-article ol { margin: 0 0 1rem 1.4rem; }
.bejson-cms-article li { margin-bottom: 0.3rem; }
.bejson-cms-article code {
  background: var(--bg-code);
  border: 1px solid var(--border-color);
  color: #FCA5A5;
  font-family: var(--font-mono);
  font-size: 0.85em;
  padding: 0.15rem 0.35rem;
  border-radius: 3px;
}
.bejson-cms-article pre {
  background: var(--bg-code);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  padding: 0.9rem;
  overflow-x: auto;
  margin: 1rem 0;
}
.bejson-cms-article pre code { background: transparent; border: none; padding: 0; color: #E2E8F0; font-size: 0.85rem; }
.bejson-cms-article blockquote {
  border-left: 3px solid var(--accent-red);
  background: rgba(222, 38, 38, 0.05);
  padding: 0.65rem 1rem;
  margin: 1rem 0;
  color: var(--text-muted);
}
.table-container { width: 100%; overflow-x: auto; margin: 1rem 0; border: 1px solid var(--border-color); border-radius: 4px; }
table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
th, td { padding: 0.55rem 0.75rem; text-align: left; border-bottom: 1px solid var(--border-color); }
th { background: var(--bg-elevated); color: var(--text-main); font-weight: 600; }
tr:last-child td { border-bottom: none; }
tr:hover td { background: rgba(255, 255, 255, 0.02); }

/* Grid & Cards for Feed / Hub */
.hub-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 0.75rem; margin-top: 1rem; }
.card {
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  transition: transform 0.15s ease, border-color 0.15s ease;
}
.card:hover { border-color: var(--accent-red); transform: translateY(-2px); }
.card-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 0.5rem; margin-bottom: 0.4rem; }
.card-title { font-weight: 700; font-size: 1.05rem; color: #fff; }
.card-badge { background: var(--bg-elevated); color: var(--text-muted); font-size: 0.7rem; padding: 0.15rem 0.4rem; border-radius: 3px; font-weight: 600; }
.card-desc { font-size: 0.825rem; color: var(--text-muted); margin-bottom: 0.75rem; line-height: 1.5; }
.card-meta { font-size: 0.75rem; color: var(--text-dim); display: flex; justify-content: space-between; border-top: 1px solid var(--border-subtle); padding-top: 0.5rem; }

/* Search Filter Box */
.search-box {
  width: 100%;
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  color: var(--text-main);
  padding: 0.6rem 0.85rem;
  border-radius: 4px;
  font-size: 0.85rem;
  margin-bottom: 1rem;
  outline: none;
}
.search-box:focus { border-color: var(--accent-red); }

/* Sidebar Drawer */
.drawer-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.65);
  backdrop-filter: blur(2px);
  z-index: 200;
  display: none;
}
.drawer-backdrop.active { display: block; }
.nav-drawer {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  width: 290px;
  background: var(--bg-surface);
  border-right: 1px solid var(--border-color);
  z-index: 201;
  transform: translateX(-100%);
  transition: transform 0.2s ease-in-out;
  display: flex;
  flex-direction: column;
}
.nav-drawer.active { transform: translateX(0); }
.drawer-header {
  height: 44px;
  padding: 0 1rem;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.drawer-close {
  background: transparent;
  border: none;
  color: var(--text-muted);
  font-size: 1.2rem;
  cursor: pointer;
}
.drawer-close:hover { color: var(--accent-red); }
.drawer-content { flex: 1; overflow-y: auto; padding: 0.75rem; }
.nav-group-title { font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-dim); margin: 0.75rem 0.25rem 0.35rem; }
.nav-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.4rem 0.6rem;
  border-radius: 4px;
  font-size: 0.825rem;
  color: var(--text-muted);
}
.nav-item:hover, .nav-item.active { background: var(--bg-elevated); color: var(--text-main); }
.nav-item.active { border-left: 2px solid var(--accent-red); }
.nav-count { font-size: 0.7rem; color: var(--text-dim); }

/* Footer */
.site-footer {
  border-top: 1px solid var(--border-color);
  padding: 1.5rem 1rem;
  background: var(--bg-surface);
  font-size: 0.75rem;
  color: var(--text-dim);
  text-align: center;
  line-height: 1.7;
}
.footer-social-links { margin-bottom: 0.4rem; display: flex; justify-content: center; gap: 1rem; font-size: 0.8rem; }
.footer-social-links a { color: var(--text-muted); }
.footer-social-links a:hover { color: var(--accent-red); }
"""

DRAWER_JS: str = """
(function() {
  'use strict';
  var menuBtn = document.getElementById('menuToggle');
  var drawer = document.getElementById('navDrawer');
  var backdrop = document.getElementById('drawerBackdrop');
  var closeBtn = document.getElementById('drawerClose');

  function openDrawer() {
    if (drawer && backdrop) {
      drawer.classList.add('active');
      backdrop.classList.add('active');
      if (menuBtn) menuBtn.setAttribute('aria-expanded', 'true');
      drawer.focus();
    }
  }

  function closeDrawer() {
    if (drawer && backdrop) {
      drawer.classList.remove('active');
      backdrop.classList.remove('active');
      if (menuBtn) menuBtn.setAttribute('aria-expanded', 'false');
      if (menuBtn) menuBtn.focus();
    }
  }

  if (menuBtn) menuBtn.addEventListener('click', openDrawer);
  if (closeBtn) closeBtn.addEventListener('click', closeDrawer);
  if (backdrop) backdrop.addEventListener('click', closeDrawer);

  window.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && drawer && drawer.classList.contains('active')) {
      closeDrawer();
    }
  });

  // Client-side quick filter for feed lists
  var searchInput = document.getElementById('searchInput');
  if (searchInput) {
    searchInput.addEventListener('input', function() {
      var query = this.value.toLowerCase().trim();
      var cards = document.querySelectorAll('.filterable-card');
      cards.forEach(function(card) {
        var text = (card.getAttribute('data-search') || '').toLowerCase();
        card.style.display = (query === '' || text.indexOf(query) !== -1) ? '' : 'none';
      });
    });
  }

  // Copy Markdown button handler
  var copyBtn = document.getElementById('copyRawBtn');
  if (copyBtn) {
    copyBtn.addEventListener('click', function() {
      var rawEl = document.getElementById('rawMarkdownContent');
      if (rawEl) {
        navigator.clipboard.writeText(rawEl.textContent).then(function() {
          copyBtn.textContent = 'Copied!';
          setTimeout(function() { copyBtn.textContent = 'Copy MD'; }, 2000);
        });
      }
    });
  }
})();
"""


class NotesSiteExporter:
    """
    Exports categorized notes from an MFDB into a clean, zero-dependency,
    static HTML5 documentation portal conforming to code-manual-builder.
    Equipped with config-driven site naming, author social links, SEO tags,
    W3C sitemap autogen, and Schema.org JSON-LD structured data.
    """

    def __init__(self, mfdb_engine: Any, output_directory: Optional[Path] = None) -> None:
        self.engine = mfdb_engine
        self.config: Dict[str, Any] = self.engine.get_configuration()
        self.output_directory: Path = (
            output_directory or (self.engine.base_directory / "exports" / "notes_site")
        ).resolve()

        # Dynamic configuration bindings
        self.site_title: str = self.config.get("site_title", "Notes Compendium")
        self.site_tagline: str = self.config.get("site_tagline", "Architecture & Technical Knowledge Hub")
        self.site_base_url: str = self.config.get("site_base_url", "https://boehnenelton2024.pages.dev/notes").rstrip("/")
        self.site_desc: str = self.config.get("site_description", "Authoritative technical notes, BEJSON specifications, and development logs.")
        self.author_name: str = self.config.get("author_name", "Elton Boehnen")
        self.author_email: str = self.config.get("author_email", "boehnenelton2024@gmail.com")
        self.author_site: str = self.config.get("author_site", "https://boehnenelton2024.pages.dev")
        self.author_github: str = self.config.get("author_github", "https://github.com/boehnenelton")
        self.author_twitter: str = self.config.get("author_twitter", "https://x.com/boehnenelton")
        self.social_image: str = self.config.get("social_share_image", "https://boehnenelton2024.pages.dev/assets/og-image.png")
        self.enable_json_ld: bool = bool(self.config.get("enable_json_ld", True))
        self.enable_og: bool = bool(self.config.get("enable_open_graph", True))
        self.enable_twitter: bool = bool(self.config.get("enable_twitter_cards", True))

    def generate_site_skeleton(self) -> None:
        """Create output directory topology."""
        self.output_directory.mkdir(parents=True, exist_ok=True)

    def render_seo_head(
        self,
        page_title: str,
        page_description: str,
        relative_canonical_path: str,
        page_type: str = "website",
        note_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Render comprehensive SEO head tags, Open Graph, Twitter Cards, and JSON-LD."""
        full_title: str = f"{page_title} · {self.site_title}"
        canonical_url: str = f"{self.site_base_url}/{relative_canonical_path.lstrip('/')}"
        clean_desc = html.escape(page_description)

        tags_meta = [
            f'<meta name="description" content="{clean_desc}">',
            f'<meta name="author" content="{html.escape(self.author_name)}">',
            f'<link rel="canonical" href="{canonical_url}">'
        ]

        # Open Graph
        if self.enable_og:
            tags_meta.extend([
                f'<meta property="og:site_name" content="{html.escape(self.site_title)}">',
                f'<meta property="og:title" content="{html.escape(full_title)}">',
                f'<meta property="og:description" content="{clean_desc}">',
                f'<meta property="og:url" content="{canonical_url}">',
                f'<meta property="og:type" content="{page_type}">',
                f'<meta property="og:image" content="{html.escape(self.social_image)}">'
            ])
            if note_metadata:
                tags_meta.append(f'<meta property="article:published_time" content="{note_metadata.get("created_at", "")}">')
                tags_meta.append(f'<meta property="article:modified_time" content="{note_metadata.get("updated_at", "")}">')
                tags_meta.append(f'<meta property="article:section" content="{html.escape(note_metadata.get("cat_name", ""))}">' )
                for t in note_metadata.get("tags", []):
                    tags_meta.append(f'<meta property="article:tag" content="{html.escape(t)}">')

        # Twitter Card
        if self.enable_twitter:
            tags_meta.extend([
                '<meta name="twitter:card" content="summary_large_image">',
                f'<meta name="twitter:title" content="{html.escape(full_title)}">',
                f'<meta name="twitter:description" content="{clean_desc}">',
                f'<meta name="twitter:image" content="{html.escape(self.social_image)}">'
            ])
            if self.author_twitter:
                twitter_handle = self.author_twitter.rstrip("/").split("/")[-1]
                if not twitter_handle.startswith("@"):
                    twitter_handle = f"@{twitter_handle}"
                tags_meta.append(f'<meta name="twitter:site" content="{twitter_handle}">')
                tags_meta.append(f'<meta name="twitter:creator" content="{twitter_handle}">')

        # Schema.org JSON-LD
        if self.enable_json_ld:
            if note_metadata:
                schema_dict = {
                    "@context": "https://schema.org",
                    "@type": "TechArticle",
                    "headline": note_metadata.get("title", ""),
                    "description": clean_desc,
                    "url": canonical_url,
                    "datePublished": note_metadata.get("created_at", ""),
                    "dateModified": note_metadata.get("updated_at", ""),
                    "articleSection": note_metadata.get("cat_name", ""),
                    "keywords": ", ".join(note_metadata.get("tags", [])),
                    "author": {
                        "@type": "Person",
                        "name": self.author_name,
                        "url": self.author_site
                    },
                    "publisher": {
                        "@type": "Organization",
                        "name": self.site_title,
                        "url": self.site_base_url
                    }
                }
            else:
                schema_dict = {
                    "@context": "https://schema.org",
                    "@type": "CollectionPage",
                    "name": full_title,
                    "description": clean_desc,
                    "url": canonical_url,
                    "publisher": {
                        "@type": "Organization",
                        "name": self.site_title,
                        "url": self.site_base_url
                    }
                }
            schema_json = json.dumps(schema_dict, indent=2)
            tags_meta.append(f'<script type="application/ld+json">\n{schema_json}\n</script>')

        return "\n  ".join(tags_meta)

    def render_nav_drawer(self, categories: List[Dict[str, Any]], active_slug: Optional[str], root_rel_path: str) -> str:
        """Render slide-out drawer containing category and recent links with full ARIA landmarks."""
        drawer_html = [
            '<div id="drawerBackdrop" class="drawer-backdrop" tabindex="-1"></div>',
            '<aside id="navDrawer" class="nav-drawer" role="dialog" aria-modal="true" aria-label="Site Navigation Drawer" tabindex="-1">',
            '  <div class="drawer-header">',
            '    <span class="brand-link">',
            f'      <span class="brand-badge">NOTES</span> {html.escape(self.site_title)}',
            '    </span>',
            '    <button id="drawerClose" class="drawer-close" aria-label="Close navigation">&times;</button>',
            '  </div>',
            '  <nav class="drawer-content" role="navigation" aria-label="Categories Navigation">',
            '    <div class="nav-group-title">Portal</div>',
            f'    <a href="{root_rel_path}index.html" class="nav-item">Master Hub</a>',
            f'    <a href="{root_rel_path}sitemap.html" class="nav-item">Site Map</a>',
            '    <div class="nav-group-title">Taxonomies</div>'
        ]

        for cat in categories:
            c_slug = cat["cat_slug"]
            c_name = html.escape(cat["cat_name"])
            c_count = cat["note_count"]
            is_active = (c_slug == active_slug)
            active_class = " active" if is_active else ""
            aria_current = ' aria-current="page"' if is_active else ''
            cat_link = f"{root_rel_path}{c_slug}/index.html"
            drawer_html.append(
                f'    <a href="{cat_link}" class="nav-item{active_class}"{aria_current}>'
                f'      <span>{c_name}</span>'
                f'      <span class="nav-count">{c_count}</span>'
                f'    </a>'
            )

        drawer_html += [
            '  </nav>',
            '</aside>'
        ]
        return "\n".join(drawer_html)

    def render_site_header(self, root_rel_path: str) -> str:
        """Render sticky top header with hamburger menu, brand badge, and social links."""
        github_link = f'<a href="{html.escape(self.author_github)}" target="_blank" rel="noopener" class="header-link" aria-label="GitHub">GitHub ↗</a>' if self.author_github else ''
        author_link = f'<a href="{html.escape(self.author_site)}" target="_blank" rel="noopener" class="header-link" aria-label="Author Website">Site ↗</a>' if self.author_site else ''

        return f"""
<a href="#mainContent" class="skip-link">Skip to main content</a>
<header class="site-header" role="banner">
  <div class="header-left">
    <button id="menuToggle" class="menu-btn" aria-expanded="false" aria-controls="navDrawer" aria-label="Toggle navigation menu">
      <span aria-hidden="true">☰</span> <span>Menu</span>
    </button>
    <a href="{root_rel_path}index.html" class="brand-link" aria-label="{html.escape(self.site_title)} Home">
      <span class="brand-badge">BEJSON</span> {html.escape(self.site_title)}
    </a>
  </div>
  <nav class="header-right" role="navigation" aria-label="Quick Links">
    <a href="{root_rel_path}sitemap.html" class="header-link">Site Map</a>
    {author_link}
    {github_link}
  </nav>
</header>
"""

    def render_site_footer(self) -> str:
        """Render clean footer with author, social links, and copyright."""
        links = []
        if self.author_site:
            links.append(f'<a href="{html.escape(self.author_site)}" target="_blank" rel="noopener">Website</a>')
        if self.author_github:
            links.append(f'<a href="{html.escape(self.author_github)}" target="_blank" rel="noopener">GitHub</a>')
        if self.author_twitter:
            links.append(f'<a href="{html.escape(self.author_twitter)}" target="_blank" rel="noopener">Twitter/X</a>')
        if self.author_email:
            links.append(f'<a href="mailto:{html.escape(self.author_email)}">Contact</a>')

        social_strip = f'<div class="footer-social-links">{" · ".join(links)}</div>' if links else ''

        return f"""
<footer class="site-footer" role="contentinfo">
  {social_strip}
  <div>BEJSON 104a MFDB v1.31 Notes Management Engine · Architected by {html.escape(self.author_name)}</div>
</footer>
"""

    def build_note_page(
        self,
        note: Dict[str, Any],
        categories: List[Dict[str, Any]],
        collocated_note_dir: Path
    ) -> None:
        """
        Build individual note documentation page:
        <category_slug>/<note_slug>/index.html
        Collocates raw markdown at <category_slug>/<note_slug>/<note_slug>.md
        """
        root_rel: str = "../../"
        cat_slug: str = slugify_text(note["cat_name"])
        note_slug: str = note["slug"]
        note_title: str = html.escape(note["title"])
        cat_name: str = html.escape(note["cat_name"])
        words: int = len(note["content"].split())
        updated_ts: str = note["updated_at"][:19]
        relative_canonical = f"{cat_slug}/{note_slug}/index.html"

        # Convert markdown body to sanitized HTML fragment
        converted_body_html: str = md_engine.convert_markdown(note["content"])

        # Tag pills
        tag_pills_html = []
        for t in note["tags"]:
            clean_tag = html.escape(t.strip().lstrip("#"))
            if clean_tag:
                tag_pills_html.append(f'<span class="tag-pill">#{clean_tag}</span>')
        tags_bar = "".join(tag_pills_html)

        # Collocate raw markdown file adhering to #tag1 #tag2 \n # title \n # category \n\n note format
        raw_md_filename = f"{note_slug}.md"
        raw_md_file_path = collocated_note_dir / raw_md_filename
        formatted_raw_md = self.engine.format_exported_markdown(
            title=note["title"],
            category_name=note["cat_name"],
            tags=note["tags"],
            content=note["content"]
        )
        with open(raw_md_file_path, "w", encoding="utf-8") as f:
            f.write(formatted_raw_md)

        # SEO & Shell Components
        excerpt = note["content"].strip().replace("\n", " ")[:160]
        seo_head = self.render_seo_head(
            page_title=note["title"],
            page_description=f"{note['title']} ({cat_name}): {excerpt}...",
            relative_canonical_path=relative_canonical,
            page_type="article",
            note_metadata=note
        )
        header_html = self.render_site_header(root_rel)
        drawer_html = self.render_nav_drawer(categories, active_slug=cat_slug, root_rel_path=root_rel)
        footer_html = self.render_site_footer()

        page_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{note_title} · {cat_name} · {html.escape(self.site_title)}</title>
  {seo_head}
  <style>{SITE_CSS}</style>
</head>
<body>
  {header_html}
  {drawer_html}

  <main id="mainContent" class="container" role="main">
    <nav class="page-bar" aria-label="Breadcrumb">
      <div class="breadcrumbs">
        <a href="{root_rel}index.html">Notes</a>
        <span class="sep" aria-hidden="true">/</span>
        <a href="../index.html">{cat_name}</a>
        <span class="sep" aria-hidden="true">/</span>
        <span class="current" aria-current="page">{note_title}</span>
      </div>
      <div class="telemetry-strip" aria-label="Note Telemetry">
        <span>{words} words</span>
        <span aria-hidden="true">•</span>
        <span>Updated: {updated_ts}</span>
      </div>
    </nav>

    <article class="article-card" role="article">
      <div class="tags-row" aria-label="Note Tags">{tags_bar}</div>
      <h1 class="article-title">{note_title}</h1>
      <div class="action-strip">
        <span style="color: var(--text-dim); font-size: 0.75rem;">Category: <a href="../index.html" style="color: var(--accent-red); font-weight:600;">{cat_name}</a></span>
        <div style="display: flex; gap: 0.5rem;">
          <a href="{raw_md_filename}" download class="action-btn" aria-label="Download raw markdown file">Raw ⤓</a>
          <button id="copyRawBtn" class="action-btn" aria-label="Copy markdown content to clipboard">Copy MD</button>
        </div>
      </div>

      <div class="bejson-cms-article">
        {converted_body_html}
      </div>

      <div id="rawMarkdownContent" style="display: none;" aria-hidden="true">{html.escape(formatted_raw_md)}</div>
    </article>
  </main>

  {footer_html}
  <script>{DRAWER_JS}</script>
</body>
</html>
"""
        index_html_path = collocated_note_dir / "index.html"
        with open(index_html_path, "w", encoding="utf-8") as f:
            f.write(page_html)

    def build_category_page(
        self,
        category: Dict[str, Any],
        category_notes: List[Dict[str, Any]],
        categories: List[Dict[str, Any]],
        category_dir: Path
    ) -> None:
        """
        Build category feed:
        <category_slug>/index.html and <category_slug>/feed.html
        """
        root_rel: str = "../"
        cat_name: str = html.escape(category["cat_name"])
        cat_slug: str = category["cat_slug"]
        cat_desc: str = html.escape(category.get("cat_description") or f"Collection of notes categorized under {cat_name}.")
        relative_canonical = f"{cat_slug}/index.html"

        seo_head = self.render_seo_head(
            page_title=category["cat_name"],
            page_description=category.get("cat_description") or f"Notes collection for {cat_name}",
            relative_canonical_path=relative_canonical,
            page_type="website"
        )
        header_html = self.render_site_header(root_rel)
        drawer_html = self.render_nav_drawer(categories, active_slug=cat_slug, root_rel_path=root_rel)
        footer_html = self.render_site_footer()

        # Render cards for notes in this category
        note_cards = []
        for n in category_notes:
            n_title = html.escape(n["title"])
            n_slug = n["slug"]
            n_words = len(n["content"].split())
            n_date = n["updated_at"][:10]
            excerpt = html.escape(n["content"].strip().replace("\n", " ")[:140])
            tags_pills = "".join([f'<span class="tag-pill" style="font-size: 0.65rem; padding: 0.1rem 0.4rem;">#{html.escape(t)}</span>' for t in n["tags"][:3]])
            search_token = html.escape(f"{n['title']} {n['content']} {' '.join(n['tags'])}")

            note_cards.append(f"""
      <article class="card filterable-card" data-search="{search_token}" role="article">
        <div class="card-header">
          <a href="{n_slug}/index.html" class="card-title">{n_title}</a>
          <span class="card-badge">{n_words}w</span>
        </div>
        <p class="card-desc">{excerpt}...</p>
        <div class="tags-row" style="margin: 0 0 0.5rem;" aria-label="Tags">{tags_pills}</div>
        <div class="card-meta">
          <span>{n_date}</span>
          <a href="{n_slug}/index.html" style="color: var(--accent-red); font-weight:600;" aria-label="Read full note: {n_title}">Read Note →</a>
        </div>
      </article>
""")

        cards_body = "\n".join(note_cards) if note_cards else '<p style="color: var(--text-dim); padding: 1rem;">No notes filed in this category yet.</p>'

        page_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{cat_name} · Categories · {html.escape(self.site_title)}</title>
  {seo_head}
  <style>{SITE_CSS}</style>
</head>
<body>
  {header_html}
  {drawer_html}

  <main id="mainContent" class="container" role="main">
    <nav class="page-bar" aria-label="Breadcrumb">
      <div class="breadcrumbs">
        <a href="{root_rel}index.html">Notes</a>
        <span class="sep" aria-hidden="true">/</span>
        <span class="current" aria-current="page">{cat_name}</span>
      </div>
      <div class="telemetry-strip">
        <span>{len(category_notes)} note(s)</span>
      </div>
    </nav>

    <div style="margin-bottom: 1rem;">
      <h1 style="font-size: 1.6rem; font-weight: 800; color: #fff; margin-bottom: 0.35rem;">{cat_name}</h1>
      <p style="color: var(--text-muted); font-size: 0.875rem;">{cat_desc}</p>
    </div>

    <input type="text" id="searchInput" class="search-box" role="searchbox" placeholder="Filter notes in {cat_name} by title, tag, or content..." aria-label="Filter notes list" autocomplete="off">

    <div class="hub-grid" role="region" aria-label="Notes in {cat_name}">
      {cards_body}
    </div>
  </main>

  {footer_html}
  <script>{DRAWER_JS}</script>
</body>
</html>
"""
        with open(category_dir / "index.html", "w", encoding="utf-8") as f:
            f.write(page_html)
        with open(category_dir / "feed.html", "w", encoding="utf-8") as f:
            f.write(page_html)

    def build_portal_index(self, categories: List[Dict[str, Any]], all_notes: List[Dict[str, Any]]) -> None:
        """Build root index.html (Master Hub)."""
        header_html = self.render_site_header(root_rel_path="./")
        drawer_html = self.render_nav_drawer(categories, active_slug=None, root_rel_path="./")
        footer_html = self.render_site_footer()

        total_notes = len(all_notes)
        total_cats = len(categories)
        total_words = sum(len(n["content"].split()) for n in all_notes)

        seo_head = self.render_seo_head(
            page_title=self.site_title,
            page_description=self.site_desc,
            relative_canonical_path="index.html",
            page_type="website"
        )

        # Build category cards
        category_cards = []
        for cat in categories:
            c_name = html.escape(cat["cat_name"])
            c_slug = cat["cat_slug"]
            c_count = cat["note_count"]
            c_desc = html.escape(cat.get("cat_description") or "Collection of categorized notes.")
            category_cards.append(f"""
      <div class="card" role="region" aria-label="Category: {c_name}">
        <div class="card-header">
          <a href="{c_slug}/index.html" class="card-title">{c_name}</a>
          <span class="card-badge" style="background: rgba(222, 38, 38, 0.15); color: #F87171;">{c_count} notes</span>
        </div>
        <p class="card-desc">{c_desc}</p>
        <div class="card-meta">
          <a href="{c_slug}/index.html" style="color: var(--accent-red); font-weight:600;" aria-label="Browse notes in {c_name}">Browse Category →</a>
        </div>
      </div>
""")

        cards_body = "\n".join(category_cards)

        # Recent notes table
        recent_rows = []
        for n in all_notes[:8]:
            c_slug = slugify_text(n["cat_name"])
            n_slug = n["slug"]
            n_title = html.escape(n["title"])
            c_name = html.escape(n["cat_name"])
            n_date = n["updated_at"][:10]
            recent_rows.append(f"""
        <tr>
          <td><a href="{c_slug}/{n_slug}/index.html" style="font-weight:600;">{n_title}</a></td>
          <td><a href="{c_slug}/index.html" style="color: var(--text-dim);">{c_name}</a></td>
          <td style="color: var(--text-dim); text-align: right;">{n_date}</td>
        </tr>
""")

        recent_table_html = "\n".join(recent_rows) if recent_rows else '<tr><td colspan="3" style="color: var(--text-dim);">No notes recorded yet.</td></tr>'

        page_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(self.site_title)} · {html.escape(self.site_tagline)}</title>
  {seo_head}
  <style>{SITE_CSS}</style>
</head>
<body>
  {header_html}
  {drawer_html}

  <main id="mainContent" class="container" role="main">
    <div class="page-bar">
      <div class="breadcrumbs">
        <span class="current" aria-current="page">Notes Knowledge Portal</span>
      </div>
      <div class="telemetry-strip" aria-label="Portal Metrics">
        <span>{total_cats} categories</span>
        <span aria-hidden="true">•</span>
        <span>{total_notes} notes</span>
        <span aria-hidden="true">•</span>
        <span>{total_words} total words</span>
      </div>
    </div>

    <div style="margin: 1.5rem 0 1rem;">
      <h1 style="font-size: 1.8rem; font-weight: 800; color: #fff; margin-bottom: 0.35rem;">{html.escape(self.site_tagline)}</h1>
      <p style="color: var(--text-muted); font-size: 0.875rem;">{html.escape(self.site_desc)}</p>
    </div>

    <div class="hub-grid" style="margin-bottom: 2rem;" role="region" aria-label="Categories Hub Grid">
      {cards_body}
    </div>

    <div style="margin: 2rem 0 0.75rem;">
      <h2 style="font-size: 1.3rem; font-weight: 700; color: #fff;">Recent Notes</h2>
    </div>
    <div class="table-container" role="region" aria-label="Recent Notes Table">
      <table>
        <thead>
          <tr>
            <th scope="col">Title</th>
            <th scope="col">Category</th>
            <th scope="col" style="text-align: right;">Updated</th>
          </tr>
        </thead>
        <tbody>
          {recent_table_html}
        </tbody>
      </table>
    </div>
  </main>

  {footer_html}
  <script>{DRAWER_JS}</script>
</body>
</html>
"""
        with open(self.output_directory / "index.html", "w", encoding="utf-8") as f:
            f.write(page_html)

    def build_sitemaps(self, categories: List[Dict[str, Any]], all_notes: List[Dict[str, Any]]) -> None:
        """Build sitemap.html, W3C sitemap.xml, and robots.txt."""
        header_html = self.render_site_header(root_rel_path="./")
        drawer_html = self.render_nav_drawer(categories, active_slug=None, root_rel_path="./")
        footer_html = self.render_site_footer()

        seo_head = self.render_seo_head(
            page_title="Site Map",
            page_description=f"Complete hierarchical sitemap of all notes and categories in {self.site_title}.",
            relative_canonical_path="sitemap.html",
            page_type="website"
        )

        sitemap_items = ['<ul style="line-height: 1.9; list-style-type: none; padding-left: 0;">']
        sitemap_items.append('  <li><a href="index.html" style="font-weight:700;">🏠 Portal Master Hub</a></li>')

        xml_urls = [
            f'  <url><loc>{self.site_base_url}/index.html</loc><changefreq>daily</changefreq><priority>1.0</priority></url>',
            f'  <url><loc>{self.site_base_url}/sitemap.html</loc><changefreq>weekly</changefreq><priority>0.5</priority></url>'
        ]

        for cat in categories:
            c_slug = cat["cat_slug"]
            c_name = html.escape(cat["cat_name"])
            cat_url = f"{self.site_base_url}/{c_slug}/index.html"
            sitemap_items.append(f'  <li style="margin-top: 0.75rem;"><a href="{c_slug}/index.html" style="font-weight:600; color: var(--accent-red);">📁 {c_name}</a></li>')
            xml_urls.append(f'  <url><loc>{cat_url}</loc><changefreq>daily</changefreq><priority>0.8</priority></url>')

            cat_notes = [n for n in all_notes if n["cat_name"].lower() == cat["cat_name"].lower()]
            if cat_notes:
                sitemap_items.append('    <ul style="list-style-type: none; padding-left: 1.5rem;">')
                for n in cat_notes:
                    n_slug = n["slug"]
                    n_title = html.escape(n["title"])
                    note_url = f"{c_slug}/{n_slug}/index.html"
                    raw_url = f"{c_slug}/{n_slug}/{n_slug}.md"
                    abs_note_url = f"{self.site_base_url}/{note_url}"
                    lastmod = n.get("updated_at", "")[:10]
                    sitemap_items.append(
                        f'      <li>📄 <a href="{note_url}">{n_title}</a> '
                        f'<span style="color: var(--text-dim); font-size: 0.75rem;">(<a href="{raw_url}">raw md</a>)</span></li>'
                    )
                    xml_urls.append(f'  <url><loc>{abs_note_url}</loc><lastmod>{lastmod}</lastmod><changefreq>weekly</changefreq><priority>0.7</priority></url>')
                sitemap_items.append('    </ul>')

        sitemap_items.append('</ul>')
        tree_html = "\n".join(sitemap_items)

        sitemap_html_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Site Map · {html.escape(self.site_title)}</title>
  {seo_head}
  <style>{SITE_CSS}</style>
</head>
<body>
  {header_html}
  {drawer_html}

  <main id="mainContent" class="container" role="main">
    <nav class="page-bar" aria-label="Breadcrumb">
      <div class="breadcrumbs">
        <a href="index.html">Notes</a>
        <span class="sep" aria-hidden="true">/</span>
        <span class="current" aria-current="page">Site Map</span>
      </div>
    </nav>

    <article class="article-card" role="article">
      <h1 class="article-title" style="margin-bottom: 1.25rem;">Complete Taxonomy Site Map</h1>
      <div class="bejson-cms-article">
        {tree_html}
      </div>
    </article>
  </main>

  {footer_html}
  <script>{DRAWER_JS}</script>
</body>
</html>
"""
        with open(self.output_directory / "sitemap.html", "w", encoding="utf-8") as f:
            f.write(sitemap_html_page)

        # XML Sitemap
        xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(xml_urls)}
</urlset>
"""
        with open(self.output_directory / "sitemap.xml", "w", encoding="utf-8") as f:
            f.write(xml_content)

        # robots.txt
        robots_content = f"""User-agent: *
Allow: /
Sitemap: {self.site_base_url}/sitemap.xml
"""
        with open(self.output_directory / "robots.txt", "w", encoding="utf-8") as f:
            f.write(robots_content)

    def export_entire_site(self) -> Dict[str, Any]:
        """
        Compile full static site:
        - Creates taxonomy directory structure: notes/<category>/<note_slug>/index.html
        - Collocates raw markdown files: <note_slug>.md
        - Emits category index and feed
        - Emits portal root index.html
        - Emits sitemaps and robots.txt
        """
        self.generate_site_skeleton()

        categories: List[Dict[str, Any]] = self.engine.list_categories()
        all_notes: List[Dict[str, Any]] = self.engine.list_notes(all_notes=True)

        generated_notes_count: int = 0
        generated_categories_count: int = 0

        # Build each category and note
        for cat in categories:
            cat_slug: str = cat["cat_slug"]
            cat_dir: Path = self.output_directory / cat_slug
            cat_dir.mkdir(parents=True, exist_ok=True)

            cat_notes = [n for n in all_notes if n["cat_name"].lower() == cat["cat_name"].lower()]

            for note in cat_notes:
                note_slug: str = note["slug"]
                note_dir: Path = cat_dir / note_slug
                note_dir.mkdir(parents=True, exist_ok=True)
                self.build_note_page(note, categories, note_dir)
                generated_notes_count += 1

            self.build_category_page(cat, cat_notes, categories, cat_dir)
            generated_categories_count += 1

        # Build portal index and sitemaps
        self.build_portal_index(categories, all_notes)
        self.build_sitemaps(categories, all_notes)

        return {
            "status": "success",
            "site_title": self.site_title,
            "site_base_url": self.site_base_url,
            "output_directory": str(self.output_directory),
            "categories_built": generated_categories_count,
            "notes_built": generated_notes_count,
            "total_notes": len(all_notes),
            "portal_index": str(self.output_directory / "index.html"),
            "sitemap_html": str(self.output_directory / "sitemap.html"),
            "sitemap_xml": str(self.output_directory / "sitemap.xml"),
            "robots_txt": str(self.output_directory / "robots.txt")
        }
