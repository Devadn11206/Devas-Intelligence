import React from 'react';
import { IntelligenceFeedView } from '../../components/intel/IntelligenceFeedView';

export const NewsPage: React.FC = () => (
  <IntelligenceFeedView
    title="AI Industry News & Engineering Blogs"
    subtitle="Tracking breaking advancements, frontier lab announcements, technical post-mortems, and engineering blogs."
    defaultContentType="article"
  />
);

export const PapersPage: React.FC = () => (
  <IntelligenceFeedView
    title="Scientific Research Papers Intelligence"
    subtitle="Continuous arXiv cs.AI/cs.LG/math.NA and Semantic Scholar tracking with structured research breakdowns."
    defaultContentType="paper"
  />
);

export const GitHubPage: React.FC = () => (
  <IntelligenceFeedView
    title="GitHub Trending & Repository Intelligence"
    subtitle="Open-source scientific machine learning, deep learning libraries, star momentum, and architectural analyses."
    defaultContentType="repo"
  />
);

export const ToolsPage: React.FC = () => (
  <IntelligenceFeedView
    title="AI Tools & Pre-trained Model Ecosystem"
    subtitle="Hugging Face model releases, weights, pipeline tags, and developer acceleration toolkits."
    defaultContentType="model,tool"
  />
);
