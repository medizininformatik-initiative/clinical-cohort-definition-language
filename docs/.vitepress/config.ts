import { withMermaid } from "vitepress-plugin-mermaid";

export default withMermaid({
    title: 'CCDL',
    description: 'Clinical Cohort Definition Language Documentation',
    ignoreDeadLinks: true,
    base: process.env.VITE_BASE_PATH || '/clinical-cohort-definition-language/',
    appearance: true,
    lastUpdated: true,
    themeConfig: {
        siteTitle: false,
        outline: false,
        aside: false,
        editLink: {
            pattern: 'https://github.com/medizininformatik-initiative/clinical-cohort-definition-language/edit/main/docs/:path',
            text: 'Edit this page on GitHub'
        },

        socialLinks: [
            { icon: 'github', link: 'https://github.com/medizininformatik-initiative/clinical-cohort-definition-language' }
        ],

        footer: {
            message: 'Released under the <a href="https://www.apache.org/licenses/LICENSE-2.0">Apache License 2.0</a>',
        },

        search: {
            provider: 'local'
        },

        nav: [
            { text: 'Home', link: '/' }
        ],

        sidebar: [
            {
                text: 'Home',
                link: '/index.md',
                activeMatch: '^/$'
            },
            {
                text: 'CCDL Documentation',
                link: '/documentation.md'
            },
            {
                text: 'CCDL Generator',
                link: '/ccdl-generator.md'
            },
            {
                text: 'Changelog',
                link: '/changelog.md'
            }
        ]
    }
})
