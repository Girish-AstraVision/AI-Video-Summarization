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
import { SpeechTranscriptPanel } from './components/speech/SpeechTranscriptPanel';
import { overviewCards, timelineEvents } from './data/mockData';
import { detectVisualObjects, generateChapters, getKeyFrames, moderateVideo, transcribeVideo } from './services/api';
import type {
  ChapterResponse,
  KeyFrameSelectionResult,
  ModerationResult,
  PreprocessingResult,
  PreprocessingState,
  SpeechToTextResult,
  VisualDetectionResult,
} from './types/api';
import type { ProcessingStep } from './types/dashboard';

function App() {
  const [videoId, setVideoId] = useState<string | null>(null);
  const [preprocessingState, setPreprocessingState] = useState<PreprocessingState>('idle');
  const [preprocessingResult, setPreprocessingResult] = useState<PreprocessingResult | null>(null);
  const [visualDetectionState, setVisualDetectionState] = useState<PreprocessingState>('idle');
  const [visualDetectionResult, setVisualDetectionResult] = useState<VisualDetectionResult | null>(null);
  const [visualDetectionError, setVisualDetectionError] = useState<string | null>(null);
  const [speechToTextState, setSpeechToTextState] = useState<PreprocessingState>('idle');
  const [speechToTextResult, setSpeechToTextResult] = useState<SpeechToTextResult | null>(null);
  const [speechToTextError, setSpeechToTextError] = useState<string | null>(null);
  const [keyFrameState, setKeyFrameState] = useState<PreprocessingState>('idle');
  const [keyFrameResult, setKeyFrameResult] = useState<KeyFrameSelectionResult | null>(null);
  const [keyFrameError, setKeyFrameError] = useState<string | null>(null);
  const [chapterState, setChapterState] = useState<PreprocessingState>('idle');
  const [chapterResult, setChapterResult] = useState<ChapterResponse | null>(null);
  const [chapterError, setChapterError] = useState<string | null>(null);
  const [moderationState, setModerationState] = useState<PreprocessingState>('idle');
  const [moderationResult, setModerationResult] = useState<ModerationResult | null>(null);
  const [moderationError, setModerationError] = useState<string | null>(null);
  const [seekToTime, setSeekToTime] = useState<number | null>(null);

  const objectSummary = useMemo(() => {
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

  const speechSummary = useMemo(() => {
    if (speechToTextState === 'in-progress') {
      return { value: 'Analyzing...', detail: 'Running Whisper...' };
    }

    if (speechToTextState === 'complete' && speechToTextResult) {
      return {
        value: String(speechToTextResult.number_of_segments),
        detail: `Detected language: ${speechToTextResult.detected_language}`,
      };
    }

    return { value: 'Not analyzed', detail: 'Not analyzed' };
  }, [speechToTextResult, speechToTextState]);

  const keyFrameSummary = useMemo(() => {
    if (keyFrameState === 'in-progress') {
      return { value: 'Analyzing...', detail: 'Selecting most relevant frames...' };
    }

    if (keyFrameState === 'complete' && keyFrameResult) {
      return {
        value: String(keyFrameResult.number_selected),
        detail: `From ${keyFrameResult.total_frames_analyzed} analyzed frames`,
      };
    }

    return { value: 'Not analyzed', detail: 'Not analyzed' };
  }, [keyFrameResult, keyFrameState]);

  const chapterSummary = useMemo(() => {
    if (chapterState === 'in-progress') {
      return { value: 'Analyzing...', detail: 'Grouping moments into chapters...' };
    }

    if (chapterState === 'complete' && chapterResult) {
      return {
        value: String(chapterResult.number_of_chapters),
        detail: chapterResult.number_of_chapters === 1 ? '1 generated chapter' : `${chapterResult.number_of_chapters} generated chapters`,
      };
    }

    return { value: 'Not analyzed', detail: 'Not analyzed' };
  }, [chapterResult, chapterState]);

  const overviewItems = useMemo(
    () => [
      overviewCards[0],
      {
        label: 'Detected Objects',
        value: objectSummary.value,
        detail: objectSummary.detail,
        tone: 'violet' as const,
      },
      {
        label: 'Speech Segments',
        value: speechSummary.value,
        detail: speechSummary.detail,
        tone: 'teal' as const,
      },
      {
        label: 'Key Frames',
        value: keyFrameSummary.value,
        detail: keyFrameSummary.detail,
        tone: 'amber' as const,
      },
      {
        label: 'Chapters',
        value: chapterSummary.value,
        detail: chapterSummary.detail,
        tone: 'blue' as const,
      },
    ],
    [chapterSummary, keyFrameSummary, objectSummary, speechSummary],
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

    const speechAnalysisValue =
      speechToTextState === 'in-progress' ? 72 : speechToTextState === 'complete' ? 100 : speechToTextState === 'failed' ? 35 : 0;

    const speechAnalysisStatus =
      speechToTextState === 'in-progress'
        ? 'In Progress'
        : speechToTextState === 'complete'
          ? 'Complete'
          : speechToTextState === 'failed'
            ? 'Failed'
            : 'Pending';

    const moderationAnalysisValue =
      moderationState === 'in-progress' ? 72 : moderationState === 'complete' ? 100 : moderationState === 'failed' ? 35 : 0;

    const moderationAnalysisStatus =
      moderationState === 'in-progress'
        ? 'In Progress'
        : moderationState === 'complete'
          ? 'Complete'
          : moderationState === 'failed'
            ? 'Failed'
            : 'Pending';

    const keyFrameAnalysisValue =
      keyFrameState === 'in-progress' ? 72 : keyFrameState === 'complete' ? 100 : keyFrameState === 'failed' ? 35 : 0;

    const keyFrameAnalysisStatus =
      keyFrameState === 'in-progress'
        ? 'In Progress'
        : keyFrameState === 'complete'
          ? 'Complete'
          : keyFrameState === 'failed'
            ? 'Failed'
            : 'Pending';

    const chapterAnalysisValue =
      chapterState === 'in-progress' ? 72 : chapterState === 'complete' ? 100 : chapterState === 'failed' ? 35 : 0;

    const chapterAnalysisStatus =
      chapterState === 'in-progress'
        ? 'In Progress'
        : chapterState === 'complete'
          ? 'Complete'
          : chapterState === 'failed'
            ? 'Failed'
            : 'Pending';

    return [
      { name: 'Upload', status: uploadStatus, value: uploadValue },
      { name: 'Preprocessing', status: preprocessingStatus, value: preprocessingValue },
      { name: 'Visual Analysis', status: visualAnalysisStatus, value: visualAnalysisValue },
      { name: 'Speech Analysis', status: speechAnalysisStatus, value: speechAnalysisValue },
      { name: 'Key Frame Selection', status: keyFrameAnalysisStatus, value: keyFrameAnalysisValue },
      { name: 'Chapters', status: chapterAnalysisStatus, value: chapterAnalysisValue },
      { name: 'Summarization', status: 'Pending', value: 0 },
      { name: 'Moderation', status: moderationAnalysisStatus, value: moderationAnalysisValue },
    ];
  }, [chapterState, keyFrameState, moderationState, preprocessingState, speechToTextState, videoId, visualDetectionState]);

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

  const handleRunSpeechAnalysis = async () => {
    if (!videoId) {
      setSpeechToTextError('Please upload a video before running speech analysis.');
      return;
    }

    setSpeechToTextState('in-progress');
    setSpeechToTextError(null);

    try {
      const result = await transcribeVideo(videoId);
      setSpeechToTextResult(result);
      setSpeechToTextState('complete');
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Whisper speech analysis failed. Please try again.';
      setSpeechToTextError(message);
      setSpeechToTextState('failed');
    }
  };

  const handleRunKeyFrameAnalysis = async () => {
    if (!videoId) {
      setKeyFrameError('Please upload a video before running key-frame selection.');
      return;
    }

    setKeyFrameState('in-progress');
    setKeyFrameError(null);

    try {
      const result = await getKeyFrames(videoId, 5);
      setKeyFrameResult(result);
      setKeyFrameState('complete');
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Key-frame selection failed. Please try again.';
      setKeyFrameError(message);
      setKeyFrameState('failed');
    }
  };

  const handleRunChapterAnalysis = async () => {
    if (!videoId) {
      setChapterError('Please upload a video before generating chapters.');
      return;
    }

    setChapterState('in-progress');
    setChapterError(null);

    try {
      const result = await generateChapters(videoId, 5);
      setChapterResult(result);
      setChapterState('complete');
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Chapter generation failed. Please try again.';
      setChapterError(message);
      setChapterState('failed');
    }
  };

  const handleRunModerationAnalysis = async () => {
    if (!videoId) {
      setModerationError('Please upload a video before running moderation analysis.');
      return;
    }

    setModerationState('in-progress');
    setModerationError(null);

    try {
      const result = await moderateVideo(videoId);
      setModerationResult(result);
      setModerationState('complete');
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Content moderation failed. Please try again.';
      setModerationError(message);
      setModerationState('failed');
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

          {preprocessingState === 'complete' ? (
            <section className="panel analysis-controls-panel" aria-label="Speech analysis controls">
              <div className="analysis-controls-row">
                <button
                  type="button"
                  className="primary-button"
                  onClick={() => {
                    void handleRunSpeechAnalysis();
                  }}
                  disabled={speechToTextState === 'in-progress'}
                >
                  {speechToTextState === 'in-progress' ? 'Running Whisper speech analysis...' : 'Run Speech Analysis'}
                </button>
              </div>
              {speechToTextError ? <div className="upload-message error-message">{speechToTextError}</div> : null}
            </section>
          ) : null}

          {preprocessingState === 'complete' ? (
            <section className="panel analysis-controls-panel" aria-label="Key-frame analysis controls">
              <div className="analysis-controls-row">
                <button
                  type="button"
                  className="primary-button"
                  onClick={() => {
                    void handleRunKeyFrameAnalysis();
                  }}
                  disabled={keyFrameState === 'in-progress'}
                >
                  {keyFrameState === 'in-progress' ? 'Selecting key frames...' : 'Run Key Frame Selection'}
                </button>
              </div>
              {keyFrameError ? <div className="upload-message error-message">{keyFrameError}</div> : null}
            </section>
          ) : null}

          {preprocessingState === 'complete' ? (
            <section className="panel analysis-controls-panel" aria-label="Chapter analysis controls">
              <div className="analysis-controls-row">
                <button
                  type="button"
                  className="primary-button"
                  onClick={() => {
                    void handleRunChapterAnalysis();
                  }}
                  disabled={chapterState === 'in-progress'}
                >
                  {chapterState === 'in-progress' ? 'Generating chapters...' : 'Run Chapter Analysis'}
                </button>
              </div>
              {chapterError ? <div className="upload-message error-message">{chapterError}</div> : null}
            </section>
          ) : null}

          {preprocessingState === 'complete' ? (
            <section className="panel analysis-controls-panel" aria-label="Moderation analysis controls">
              <div className="analysis-controls-row">
                <button
                  type="button"
                  className="primary-button"
                  onClick={() => {
                    void handleRunModerationAnalysis();
                  }}
                  disabled={moderationState === 'in-progress'}
                >
                  {moderationState === 'in-progress' ? 'Running content moderation...' : 'Run Moderation Check'}
                </button>
              </div>
              {moderationError ? <div className="upload-message error-message">{moderationError}</div> : null}
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

          {speechToTextResult ? (
            <SpeechTranscriptPanel
              result={speechToTextResult}
              onTimestampClick={handleTimestampSeek}
              isVisible={speechToTextState !== 'idle'}
            />
          ) : null}

          {keyFrameResult ? (
            <KeyFrameGallery
              result={keyFrameResult}
              onTimestampClick={handleTimestampSeek}
              isVisible={keyFrameState !== 'idle'}
            />
          ) : null}

          {moderationResult ? (
            <ModerationPanel
              result={moderationResult}
              onTimestampClick={handleTimestampSeek}
              isVisible={moderationState !== 'idle'}
            />
          ) : null}

          <section className="summary-grid">
            <SummaryPanel />
          </section>

          {chapterResult ? (
            <section className="content-grid two-column">
              <ChapterList result={chapterResult} onTimestampClick={handleTimestampSeek} isVisible={chapterState !== 'idle'} />
              <EventTimeline events={timelineEvents} />
            </section>
          ) : (
            <section className="content-grid two-column">
              <EventTimeline events={timelineEvents} />
            </section>
          )}

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
