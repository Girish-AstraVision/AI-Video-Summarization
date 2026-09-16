import { useRef, useState } from 'react';
import { preprocessVideo, uploadVideo } from '../../services/api';
import type { PreprocessingResult, PreprocessingState, UploadVideoResponse } from '../../types/api';

type UploadCardProps = {
  videoId: string | null;
  onUploadSuccess: (videoId: string) => void;
  onPreprocessStateChange: (state: PreprocessingState) => void;
  onPreprocessResult: (result: PreprocessingResult | null) => void;
};

const allowedExtensions = ['.mp4', '.mov', '.avi', '.mkv'];
const frontendSizeLimitBytes = 500 * 1024 * 1024;

function formatFileSize(bytes: number): string {
  if (bytes === 0) {
    return '0 B';
  }

  const units = ['B', 'KB', 'MB', 'GB'];
  const unitIndex = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / 1024 ** unitIndex;

  return `${value.toFixed(value >= 10 || unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}

function formatDuration(seconds: number | null): string {
  if (seconds === null || Number.isNaN(seconds)) {
    return 'N/A';
  }

  const totalSeconds = Math.max(0, Math.round(seconds));
  const minutes = Math.floor(totalSeconds / 60);
  const remainingSeconds = totalSeconds % 60;

  return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
}

function getValidationError(file: File | null): string | null {
  if (!file) {
    return 'Please select a video file to upload.';
  }

  if (file.size <= 0) {
    return 'The selected file is empty. Please choose a non-empty video file.';
  }

  const extension = file.name.slice(file.name.lastIndexOf('.')).toLowerCase();
  if (!allowedExtensions.includes(extension)) {
    return 'Unsupported file format. Please upload a video in MP4, MOV, AVI, or MKV format.';
  }

  if (file.size > frontendSizeLimitBytes) {
    return 'The selected video exceeds the 500 MB frontend validation limit. Please choose a smaller file.';
  }

  return null;
}

function getUploadErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  return 'The upload failed. Please try again.';
}

export function UploadCard({ videoId, onUploadSuccess, onPreprocessStateChange, onPreprocessResult }: UploadCardProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<UploadVideoResponse | null>(null);
  const [preprocessingResult, setPreprocessingResult] = useState<PreprocessingResult | null>(null);

  const handleSelectedFile = (file: File | null) => {
    setError(null);
    setSuccess(null);
    onPreprocessStateChange('idle');
    onPreprocessResult(null);
    setPreprocessingResult(null);

    const validationError = getValidationError(file);
    if (validationError) {
      setError(validationError);
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const nextFile = event.target.files?.[0] ?? null;
    handleSelectedFile(nextFile);
  };

  const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(false);
    const droppedFile = event.dataTransfer.files?.[0] ?? null;
    handleSelectedFile(droppedFile);
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Please select a video file before uploading.');
      return;
    }

    const validationError = getValidationError(selectedFile);
    if (validationError) {
      setError(validationError);
      return;
    }

    setIsUploading(true);
    setError(null);

    try {
      const uploadResponse = await uploadVideo(selectedFile);
      setSuccess(uploadResponse);
      onUploadSuccess(uploadResponse.video_id);
      setError(null);
    } catch (caughtError) {
      setSuccess(null);
      setError(getUploadErrorMessage(caughtError));
    } finally {
      setIsUploading(false);
    }
  };

  const handlePreprocess = async () => {
    if (!videoId) {
      setError('Please upload a video before starting analysis.');
      return;
    }

    setIsProcessing(true);
    setError(null);
    onPreprocessStateChange('in-progress');

    try {
      const result = await preprocessVideo(videoId);
      setPreprocessingResult(result);
      onPreprocessResult(result);
      onPreprocessStateChange('complete');
      setError(null);
    } catch (caughtError) {
      const message = getUploadErrorMessage(caughtError);
      onPreprocessResult(null);
      onPreprocessStateChange('failed');
      setError(message);
      setPreprocessingResult(null);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <section className="panel upload-panel">
      <div
        className={`upload-card ${isDragging ? 'is-dragging' : ''}`}
        onDragOver={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            fileInputRef.current?.click();
          }
        }}
      >
        <input
          ref={fileInputRef}
          type="file"
          hidden
          accept=".mp4,.mov,.avi,.mkv,video/mp4,video/quicktime,video/x-msvideo,video/x-matroska"
          onChange={handleFileChange}
        />

        <div className="upload-icon" aria-hidden="true">
          ⇪
        </div>

        <h3>Upload a video to begin analysis</h3>
        <p className="upload-subtitle">Analyze video, audio, speech and visual content using AI</p>

        <div className="supported-formats" aria-label="Supported video formats">
          <span>Supported formats:</span>
          <div className="format-list">
            <span>MP4</span>
            <span>MOV</span>
            <span>AVI</span>
            <span>MKV</span>
          </div>
        </div>

        <div className="dropzone-box" aria-label="Drag and drop upload area">
          <div className="dropzone-text">Drag &amp; drop your video here</div>
          <span className="dropzone-or">or</span>
          <span className="dropzone-hint">choose a file from your computer</span>
        </div>

        <div className="upload-actions">
          <button
            type="button"
            className="primary-button upload-button"
            onClick={(event) => {
              event.stopPropagation();
              fileInputRef.current?.click();
            }}
            disabled={isUploading || isProcessing}
          >
            {isUploading ? 'Uploading...' : 'Choose Video'}
          </button>

          {selectedFile ? (
            <button
              type="button"
              className="secondary-button upload-submit-button"
              onClick={(event) => {
                event.stopPropagation();
                void handleUpload();
              }}
              disabled={isUploading || isProcessing}
            >
              Upload Video
            </button>
          ) : null}
        </div>

        {selectedFile ? (
          <div className="file-meta-box" aria-live="polite">
            <div>
              <span className="meta-label">Selected file</span>
              <strong>{selectedFile.name}</strong>
            </div>
            <div>
              <span className="meta-label">Size</span>
              <strong>{formatFileSize(selectedFile.size)}</strong>
            </div>
            <div>
              <span className="meta-label">Status</span>
              <strong>Ready to upload</strong>
            </div>
          </div>
        ) : null}

        {error ? <div className="upload-message error-message">{error}</div> : null}

        {success ? (
          <div className="upload-message success-message" aria-live="polite">
            <strong>Upload successful</strong>
            <div className="success-metadata-grid">
              <div className="success-metadata-item">
                <span>Original filename</span>
                <strong>{success.original_filename}</strong>
              </div>
              <div className="success-metadata-item">
                <span>Video ID</span>
                <strong>{success.video_id}</strong>
              </div>
              <div className="success-metadata-item">
                <span>File size</span>
                <strong>{formatFileSize(success.file_size)}</strong>
              </div>
              <div className="success-metadata-item">
                <span>Processing status</span>
                <strong>{success.status}</strong>
              </div>
            </div>
          </div>
        ) : null}

        {videoId && !isProcessing ? (
          <button
            type="button"
            className="primary-button process-button"
            onClick={(event) => {
              event.stopPropagation();
              void handlePreprocess();
            }}
          >
            Start Analysis
          </button>
        ) : null}

        {isProcessing ? (
          <button type="button" className="secondary-button process-button" disabled>
            Processing video...
          </button>
        ) : null}

        {preprocessingResult ? (
          <div className="preprocessing-summary" aria-live="polite">
            <div className="preprocessing-summary-header">Preprocessing complete</div>
            <div className="preprocessing-summary-grid">
              <div className="preprocessing-item"><span>Duration</span><strong>{formatDuration(preprocessingResult.metadata.duration)}</strong></div>
              <div className="preprocessing-item"><span>Resolution</span><strong>{preprocessingResult.metadata.width && preprocessingResult.metadata.height ? `${preprocessingResult.metadata.width} × ${preprocessingResult.metadata.height}` : 'N/A'}</strong></div>
              <div className="preprocessing-item"><span>FPS</span><strong>{preprocessingResult.metadata.fps ?? 'N/A'}</strong></div>
              <div className="preprocessing-item"><span>Frames</span><strong>{preprocessingResult.frame_count}</strong></div>
              <div className="preprocessing-item"><span>Audio</span><strong>{preprocessingResult.metadata.audio_present ? 'Extracted' : 'Not present'}</strong></div>
              <div className="preprocessing-item"><span>Status</span><strong>{preprocessingResult.preprocessing_status}</strong></div>
            </div>
          </div>
        ) : null}

        {videoId ? <div className="upload-state">Stored video ID: {videoId}</div> : null}
      </div>
    </section>
  );
}
