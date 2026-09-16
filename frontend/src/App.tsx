import { useMemo, useState } from 'react';
import './App.css';
import { Sidebar } from './components/layout/Sidebar';
import { Header } from './components/layout/Header';
import { OverviewCard } from './components/dashboard/OverviewCard';
import { ProcessingStatus } from './components/dashboard/ProcessingStatus';
import { UploadCard } from './components/video/UploadCard';
import { VideoWorkspace } from './components/video/VideoWorkspace';
import { SummaryPanel } from './components/summary/SummaryPanel';
import { ChapterList } from './components/chapters/ChapterList';
import { KeyFrameGallery } from './components/keyframes/KeyFrameGallery';
import { ModerationPanel } from './components/moderation/ModerationPanel';
import { EventTimeline } from './components/timeline/EventTimeline';
import { VisualDetectionPanel } from './components/visual/VisualDetectionPanel';
import { chapterItems, keyFrameItems, moderationItems, overviewCards, timelineEvents } from './data/mockData';
import { detectVisualObjects } from './services/api';
import type { PreprocessingResult, PreprocessingState, VisualDetectionResult } from './types/api';
import type { ProcessingStep } from './types/dashboard';

function App() {
  const [videoId, setVideoId] = useState<string | null>(null);
  const [preprocessingState, setPreprocessingState] = useState<PreprocessingState>('idle');
  const [preprocessingResult, setPreprocessingResult] = useState<PreprocessingResult | null>(null);
  const [visualDetectionState, setVisualDetectionState] = useState<PreprocessingState>('idle');
  const [visualDetectionResult, setVisualDetectionResult] = useState<VisualDetectionResult | null>(null);
  const [visualDetectionError, setVisualDetectionError] = useState<string | null>(null);
  const [seekToTime, setSeekToTime] = useState<number | null>(null);

  const overviewSummary = useMemo(() => {
    if (visualDetectionState === 'in-progress') {
      return { value: 'Analyzing...', detail: 'Analyzing...' };
    }

    if (visualDetectionState === 'complete' && visualDetectionResult) {
      const uniqueClasses = new Set(visualDetectionResult.detections.map((detection) => detection.label)).size;
      return {
        value: String(visualDetectionResult.number_of_detections),
        detail: `Across ${uniqueClasses} classes`,
      };
    }

    if (visualDetectionResult) {
      const uniqueClasses = new Set(visualDetectionResult.detections.map((detection) => detection.label)).size;
      return {
        value: String(visualDetectionResult.number_of_detections),
        detail: `Across ${uniqueClasses} classes`,
      };
    }

    return { value: 'Not analyzed', detail: 'Not analyzed' };
  }, [visualDetectionResult, visualDetectionState]);

  const overviewItems = useMemo(
    () => [
      ...overviewCards.slice(0, 1),
      {
        label: 'Detected Objects',
        value: overviewSummary.value,
        detail: overviewSummary.detail,
        tone: 'violet' as const,
      },
      ...overviewCards.slice(2),
    ],
    [overviewSummary],
  );

  const processingSteps = useMemo<ProcessingStep[]>(() => {
    const uploadValue = videoId ? 100 : 0;
    const uploadStatus = videoId ? 'Complete' : 'Pending';

    const preprocessingValue =
      preprocessingState === 'in-progress' ? 72 : preprocessingState === 'complete' ? 100 : preprocessingState === 'failed' ? 40 : 0;

    const preprocessingStatus =
      preprocessingState === 'in-progress'
        ? 'In Progress'
        : preprocessingState === 'complete'
          ? 'Complete'
          : preprocessingState === 'failed'
            ? 'Failed'
            : 'Pending';

    const visualAnalysisValue =
      visualDetectionState === 'in-progress' ? 72 : visualDetectionState === 'complete' ? 100 : visualDetectionState === 'failed' ? 35 : 0;

    const visualAnalysisStatus =
      visualDetectionState === 'in-progress'
        ? 'In Progress'
        : visualDetectionState === 'complete'
          ? 'Complete'
          : visualDetectionState === 'failed'
            ? 'Failed'
            : 'Pending';

    return [
      { name: 'Upload', status: uploadStatus, value: uploadValue },
      { name: 'Preprocessing', status: preprocessingStatus, value: preprocessingValue },
      { name: 'Visual Analysis', status: visualAnalysisStatus, value: visualAnalysisValue },
      { name: 'Speech Analysis', status: 'Pending', value: 0 },
      { name: 'Summarization', status: 'Pending', value: 0 },
      { name: 'Moderation', status: 'Pending', value: 0 },
    ];
  }, [preprocessingState, videoId, visualDetectionState]);

  const handleRunVisualAnalysis = async () => {
    if (!videoId) {
      setVisualDetectionError('Please upload a video before running visual analysis.');
      return;
    }

    setVisualDetectionState('in-progress');
    setVisualDetectionError(null);

    try {
      const result = await detectVisualObjects(videoId, 0.5);
      setVisualDetectionResult(result);
      setVisualDetectionState('complete');
    } catch (error) {
      const message = error instanceof Error ? error.message : 'RT-DETR visual analysis failed. Please try again.';
      setVisualDetectionError(message);
      setVisualDetectionState('failed');
    }
  };

  const handleTimestampSeek = (timestamp: number) => {
    setSeekToTime(timestamp);
  };

  return (
    <div className="app-shell">
      <Header />

      <div className="main-layout">
        <Sidebar />

        <main className="content-area">
          <section className="welcome-panel">
            <div>
              <p className="eyebrow">AI Video Analysis</p>
              <h1>AI Video Analysis</h1>
            </div>
            <p className="welcome-copy">
              This system analyzes video, audio, speech, and visual events to extract meaningful
              insights from raw content. It combines multimodal cues to generate summaries, detect
              key moments, and identify content-sensitive patterns.
            </p>
          </section>

          <UploadCard
            videoId={videoId}
            onUploadSuccess={setVideoId}
            onPreprocessStateChange={setPreprocessingState}
            onPreprocessResult={setPreprocessingResult}
          />

          <section className="overview-grid" aria-label="Analysis overview cards">
            {overviewItems.map((item) => (
              <OverviewCard key={item.label} item={item} />
            ))}
          </section>

          {preprocessingState === 'complete' ? (
            <section className="panel analysis-controls-panel" aria-label="Visual analysis controls">
              <div className="analysis-controls-row">
                <button
                  type="button"
                  className="primary-button"
                  onClick={() => {
                    void handleRunVisualAnalysis();
                  }}
                  disabled={visualDetectionState === 'in-progress'}
                >
                  {visualDetectionState === 'in-progress' ? 'Running RT-DETR visual analysis...' : 'Run Visual Analysis'}
                </button>
              </div>
              {visualDetectionError ? <div className="upload-message error-message">{visualDetectionError}</div> : null}
            </section>
          ) : null}

          <section className="workspace-grid">
            <VideoWorkspace videoId={videoId} seekToTime={seekToTime} onSeekHandled={() => setSeekToTime(null)} />
            <ProcessingStatus steps={processingSteps} />
          </section>

          {visualDetectionResult ? (
            <VisualDetectionPanel
              result={visualDetectionResult}
              onTimestampClick={handleTimestampSeek}
              isVisible={visualDetectionState !== 'idle'}
            />
          ) : null}

          <section className="summary-grid">
            <SummaryPanel />
          </section>

          <section className="content-grid two-column">
            <ChapterList chapters={chapterItems} />
            <KeyFrameGallery items={keyFrameItems} />
          </section>

          <section className="content-grid two-column">
            <ModerationPanel items={moderationItems} />
            <EventTimeline events={timelineEvents} />
          </section>

          {preprocessingResult ? (
            <section className="panel preprocessing-result-panel" aria-live="polite">
              <div className="panel-heading">
                <h3>Preprocessing Results</h3>
              </div>

              <div className="preprocessing-grid">
                <div className="metric-item">
                  <span className="metric-label">Duration</span>
                  <strong>{preprocessingResult.metadata.duration ?? 'N/A'}</strong>
                </div>
                <div className="metric-item">
                  <span className="metric-label">Resolution</span>
                  <strong>
                    {preprocessingResult.metadata.width && preprocessingResult.metadata.height
                      ? `${preprocessingResult.metadata.width} × ${preprocessingResult.metadata.height}`
                      : 'N/A'}
                  </strong>
                </div>
                <div className="metric-item">
                  <span className="metric-label">FPS</span>
                  <strong>{preprocessingResult.metadata.fps ?? 'N/A'}</strong>
                </div>
                <div className="metric-item">
                  <span className="metric-label">Frames</span>
                  <strong>{preprocessingResult.frame_count}</strong>
                </div>
                <div className="metric-item">
                  <span className="metric-label">Audio</span>
                  <strong>{preprocessingResult.metadata.audio_present ? 'Extracted' : 'Not present'}</strong>
                </div>
                <div className="metric-item">
                  <span className="metric-label">Status</span>
                  <strong>{preprocessingResult.preprocessing_status}</strong>
                </div>
              </div>
            </section>
          ) : null}
        </main>
      </div>
    </div>
  );
}

export default App;
