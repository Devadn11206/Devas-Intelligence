import React from 'react';
import { IntelligenceFeedView } from '../../components/intel/IntelligenceFeedView';

export const OverviewPage: React.FC = () => {
  return (
    <IntelligenceFeedView
      title="Global AI Technology Intelligence Radar"
      subtitle="Unified cross-domain stream of research papers, open-source code repositories, model weights, and technical news."
    />
  );
};
