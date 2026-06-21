import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'RAGForge',
  tagline: 'One workshop for building, evaluating, and optimizing RAG — usable from any language',
  favicon: 'img/ragforge-mascot.png',

  url: 'https://rag-forge-o1d8.vercel.app',
  baseUrl: '/',

  organizationName: 'samsuljahith',
  projectName: 'RagForge',

  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  markdown: {
    mermaid: true,
  },

  themes: ['@docusaurus/theme-mermaid'],

  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.ts',
          editUrl: 'https://github.com/samsuljahith/RagForge/tree/main/website/',
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    colorMode: {
      defaultMode: 'dark',
      disableSwitch: true,
      respectPrefersColorScheme: false,
    },
    navbar: {
      title: 'RAGForge',
      logo: {
        alt: 'RAGForge mascot',
        src: 'img/ragforge-mascot.png',
        width: 32,
        height: 32,
      },
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'docsSidebar',
          position: 'left',
          label: 'Docs',
        },
        {
          to: '/docs/guides/pipeline',
          label: 'Features',
          position: 'left',
        },
        {
          to: '/docs/reference/http-api',
          label: 'API',
          position: 'left',
        },
        {
          href: 'https://github.com/samsuljahith/RagForge',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Docs',
          items: [
            {label: 'Quickstart', to: '/docs/getting-started/quickstart'},
            {label: 'API Reference', to: '/docs/reference/http-api'},
            {label: 'CLI Reference', to: '/docs/reference/cli'},
          ],
        },
        {
          title: 'Links',
          items: [
            {label: 'GitHub', href: 'https://github.com/samsuljahith/RagForge'},
            {label: 'Issues', href: 'https://github.com/samsuljahith/RagForge/issues'},
            {label: 'PyPI', href: 'https://pypi.org/project/ragforge/'},
          ],
        },
      ],
      copyright: `Apache-2.0 · RAGForge Contributors · ${new Date().getFullYear()}`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['bash', 'python', 'json', 'javascript'],
    },
    mermaid: {
      theme: {light: 'neutral', dark: 'dark'},
    },
  } satisfies Preset.ThemeConfig,

  plugins: [
    [
      require.resolve('@easyops-cn/docusaurus-search-local'),
      {
        hashed: true,
        language: ['en'],
        highlightSearchTermsOnTargetPage: true,
        explicitSearchResultPath: true,
      },
    ],
  ],
};

export default config;
