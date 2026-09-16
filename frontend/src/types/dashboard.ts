export type OverviewCard = {
  label: string;
  value: string;
  detail: string;
  tone: 'blue' | 'violet' | 'teal' | 'amber';
};

export type ChapterItem = {
  timestamp: string;
  title: string;
  description: string;
};

export type KeyFrameItem = {
  timestamp: string;
  importance: 'High' | 'Medium' | 'Low';
  title: string;
};

export type ModerationItem = {
  status: 'Safe Content' | 'Review Required' | 'Flagged Content';
  timestamp: string;
  event: string;
  severity: 'Low' | 'Medium' | 'High';
};

export type ProcessingStep = {
  name: string;
  status: 'Complete' | 'In Progress' | 'Pending' | 'Failed';
  value: number;
};
