import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  docsSidebar: [
    {
      type: 'category',
      label: 'Getting Started',
      items: [
        'getting-started/introduction',
        'getting-started/installation',
        'getting-started/quickstart',
      ],
    },
    {
      type: 'category',
      label: 'Core Concepts',
      items: [
        'core-concepts/architecture',
        'core-concepts/documents-and-chunks',
        'core-concepts/plugin-registry',
      ],
    },
    {
      type: 'category',
      label: 'Guides',
      items: [
        'guides/parsing',
        'guides/chunking',
        'guides/pipeline',
        'guides/evaluation',
        'guides/quantization',
        'guides/migration',
      ],
    },
    {
      type: 'category',
      label: 'Using from Any Language',
      items: [
        'any-language/overview',
        'any-language/clients',
      ],
    },
    {
      type: 'category',
      label: 'Reference',
      items: [
        'reference/cli',
        'reference/http-api',
        'reference/python-api',
      ],
    },
    'contributing',
  ],
};

export default sidebars;
