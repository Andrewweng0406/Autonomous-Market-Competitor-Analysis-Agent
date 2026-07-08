import type { FinalReport } from '@/lib/api'

// Illustrative report used for the "sample report" preview when no backend
// is connected. Real analyses come from the API.
export const SAMPLE_REPORT: FinalReport = {
  subject: 'Collaborative workspace for engineering teams',
  executive_summary:
    'The engineering-focused collaborative workspace category sits at the intersection of two large, growing markets: knowledge management and developer productivity. Incumbents like Notion and Confluence own general-purpose documentation, but leave a gap for a tool purpose-built around engineering workflows — code-aware docs, tight VCS integration, and technical review flows. The opportunity is real but crowded; differentiation will hinge on deep developer-tool integrations and a defensible collaboration graph rather than yet another wiki.',
  swot: {
    strengths: [
      'Clear, underserved wedge: engineering-native documentation',
      'High switching costs once a team standardizes its knowledge base',
      'Natural expansion into adjacent workflows (RFCs, incident retros)',
    ],
    weaknesses: [
      'No existing distribution or brand recognition',
      'Feature parity with Notion/Confluence is capital intensive',
      'Onboarding friction competing against free incumbents',
    ],
    opportunities: [
      'AI-assisted authoring and search over technical knowledge',
      'Deep integrations with GitHub, Linear, and CI/CD tooling',
      'Bottom-up PLG motion inside engineering orgs',
    ],
    threats: [
      'Notion and Atlassian shipping engineering-specific features',
      'GitHub extending Wikis and Discussions natively',
      'Long enterprise sales cycles slowing net-new adoption',
    ],
  },
  competitors: [
    {
      name: 'Notion',
      description:
        'General-purpose workspace combining docs, wikis, and lightweight project management with a large prosumer base.',
      strengths: ['Flexible blocks', 'Strong brand', 'Massive template ecosystem'],
      weaknesses: ['Weak code support', 'Performance at scale', 'Shallow dev integrations'],
      estimated_market_position: 'Category leader',
      website: 'https://notion.so',
    },
    {
      name: 'Confluence',
      description:
        'Atlassian’s enterprise wiki, tightly bundled with Jira and widely deployed across large engineering organizations.',
      strengths: ['Jira integration', 'Enterprise trust', 'Governance controls'],
      weaknesses: ['Dated UX', 'Slow editing', 'Poor bottom-up adoption'],
      estimated_market_position: 'Enterprise incumbent',
      website: 'https://www.atlassian.com/software/confluence',
    },
    {
      name: 'GitBook',
      description:
        'Documentation platform popular for developer docs and internal knowledge, with Git-based sync.',
      strengths: ['Git sync', 'Clean reading UX', 'Developer-friendly'],
      weaknesses: ['Limited collaboration', 'Narrow scope', 'Smaller ecosystem'],
      estimated_market_position: 'Niche challenger',
      website: 'https://gitbook.com',
    },
  ],
  market_trends: [
    {
      title: 'AI-native knowledge retrieval',
      description:
        'Teams increasingly expect semantic search and generative answers over their internal documentation rather than manual navigation.',
      impact: 'high',
    },
    {
      title: 'Consolidation of the tool stack',
      description:
        'Budget pressure is pushing engineering orgs to reduce point tools, favoring platforms that span docs, planning, and workflows.',
      impact: 'medium',
    },
    {
      title: 'Shift toward async, written culture',
      description:
        'Distributed teams continue to formalize written RFCs and decision records, expanding demand for structured docs.',
      impact: 'medium',
    },
    {
      title: 'Open-source documentation frameworks',
      description:
        'Free static-site doc generators keep a portion of the market from paying for hosted tools.',
      impact: 'low',
    },
  ],
  sources: [
    {
      title: 'Notion pricing and feature overview (2026)',
      url: 'https://notion.so/pricing',
      snippet:
        'Notion’s free tier and per-seat pricing set the anchor for prosumer collaboration tooling.',
    },
    {
      title: 'Atlassian Q4 earnings — Confluence adoption',
      url: 'https://investor.atlassian.com',
      snippet:
        'Confluence continues steady growth within existing enterprise Jira accounts.',
    },
    {
      title: 'State of Developer Productivity 2026',
      url: 'https://example.com/dev-productivity-report',
      snippet:
        'Survey data shows engineers spend ~20% of time searching for internal knowledge.',
    },
  ],
  markdown_report: `## Executive Summary

The engineering-focused collaborative workspace category sits at the intersection of **knowledge management** and **developer productivity**. Incumbents own general-purpose documentation but leave a gap for a tool purpose-built around engineering workflows.

## Market Overview

| Segment | Est. Size | Growth |
| --- | --- | --- |
| Knowledge management | $18B | 12% CAGR |
| Developer productivity | $9B | 22% CAGR |

## Competitive Landscape

1. **Notion** — category leader, weak code support
2. **Confluence** — enterprise incumbent, dated UX
3. **GitBook** — niche challenger, Git-native

## Recommendation

Enter through an **engineering-native wedge** with deep VCS and issue-tracker integrations, then expand into adjacent workflows (RFCs, incident retrospectives). Differentiate on a defensible collaboration graph rather than editor features alone.
`,
}
