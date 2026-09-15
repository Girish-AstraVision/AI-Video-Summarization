import { API_BASE_URL } from '../../config/env';

type VideoWorkspaceProps = {
  videoId: string | null;
};

export function VideoWorkspace({ videoId }: VideoWorkspaceProps) {
  const videoUrl = videoId ? `${API_BASE_URL}/api/videos/${encodeURIComponent(videoId)}/stream` : null;

  return (
    <section className="panel video-panel">
      <div className="video-stage">
        {videoUrl ? (
          <video
            className="video-element"
            src={videoUrl}
            controls
            preload="metadata"
            playsInline
            aria-label="Uploaded video preview"
          />
        ) : (
          <>
            <button type="button" className="play-button" aria-label="Play preview" disabled>
              ▶
            </button>
            <div className="video-empty-state">
              <span>Upload a video to preview it here</span>
            </div>
          </>
        )}

        {videoUrl ? (
          <div className="video-overlay">
            <span className="video-timestamp">Live preview</span>
          </div>
        ) : null}

        {videoUrl ? (
          <div className="video-progress" aria-label="Video progress">
            <span style={{ width: '0%' }} />
          </div>
        ) : null}
      </div>
    </section>
  );
}
