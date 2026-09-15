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
        <p>Supported formats: MP4, MOV, AVI, MKV</p>

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
          </div>
        ) : null}

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
              Upload selected file
            </button>
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
        </div>

        {error ? <div className="upload-message error-message">{error}</div> : null}

        {success ? (
          <div className="upload-message success-message" aria-live="polite">
            <strong>Upload successful</strong>
            <span>Original filename: {success.original_filename}</span>
            <span>Video ID: {success.video_id}</span>
            <span>File size: {formatFileSize(success.file_size)}</span>
            <span>Status: {success.status}</span>
          </div>
        ) : null}

        {preprocessingResult ? (
          <div className="preprocessing-summary" aria-live="polite">
            <div className="preprocessing-summary-header">Preprocessing complete</div>
            <div className="preprocessing-summary-grid">
              <span>Duration: {formatDuration(preprocessingResult.metadata.duration)}</span>
              <span>Resolution: {preprocessingResult.metadata.width && preprocessingResult.metadata.height ? `${preprocessingResult.metadata.width} × ${preprocessingResult.metadata.height}` : 'N/A'}</span>
              <span>FPS: {preprocessingResult.metadata.fps ?? 'N/A'}</span>
              <span>Frames: {preprocessingResult.frame_count}</span>
              <span>Audio: {preprocessingResult.metadata.audio_present ? 'Extracted' : 'Not present'}</span>
              <span>Status: {preprocessingResult.preprocessing_status}</span>
            </div>
          </div>
        ) : null}

        {videoId ? <div className="upload-state">Stored video ID: {videoId}</div> : null}
      </div>
    </section>
  );
}
