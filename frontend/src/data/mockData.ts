import type {
  ChapterItem,
  KeyFrameItem,
  ModerationItem,
  OverviewCard,
  ProcessingStep,
} from '../types/dashboard';

export const overviewCards: OverviewCard[] = [
  { label: 'Video Duration', value: '01:03', detail: 'Full clip length', tone: 'blue' },
  { label: 'Detected Objects', value: '24', detail: 'Across 6 classes', tone: 'violet' },
  { label: 'Speech Segments', value: '12', detail: 'Transcribed audio events', tone: 'teal' },
  { label: 'Moderation Alerts', value: '03', detail: '2 flagged / 1 review', tone: 'amber' },
];

export const chapterItems: ChapterItem[] = [
  { timestamp: '00:00', title: 'Introduction', description: 'Scene setup and project overview.' },
  { timestamp: '00:13', title: 'Feature Highlight', description: 'Primary object is introduced in detail.' },
  { timestamp: '00:28', title: 'Operational Walkthrough', description: 'System controls and usage sequence.' },
  { timestamp: '00:46', title: 'Benefits Overview', description: 'Performance and output advantages are discussed.' },
  { timestamp: '00:58', title: 'Closing Summary', description: 'Final recap and closing remarks.' },
];

export const keyFrameItems: KeyFrameItem[] = [
  { timestamp: '00:06', importance: 'High', title: 'Product reveal' },
  { timestamp: '00:19', importance: 'High', title: 'Object tracking' },
  { timestamp: '00:31', importance: 'Medium', title: 'Workflow close-up' },
  { timestamp: '00:49', importance: 'Low', title: 'Scene transition' },
];

export const moderationItems: ModerationItem[] = [
  { status: 'Safe Content', timestamp: '00:11', event: 'Object classification passed', severity: 'Low' },
  { status: 'Review Required', timestamp: '00:37', event: 'Sensitive phrase detected in speech', severity: 'Medium' },
  { status: 'Flagged Content', timestamp: '00:54', event: 'Potential restricted keyword match', severity: 'High' },
];

export const processingSteps: ProcessingStep[] = [
  { name: 'Upload', status: 'Complete', value: 100 },
  { name: 'Preprocessing', status: 'Complete', value: 100 },
  { name: 'Visual Analysis', status: 'In Progress', value: 82 },
  { name: 'Speech Analysis', status: 'In Progress', value: 70 },
  { name: 'Summarization', status: 'Pending', value: 35 },
  { name: 'Moderation', status: 'Pending', value: 20 },
];
