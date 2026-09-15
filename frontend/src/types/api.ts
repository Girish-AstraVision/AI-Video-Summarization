export interface ApiHealthResponse {
  status?: string;
  message?: string;
  version?: string;
}

export type UploadStatus = 'uploaded';

export interface UploadVideoResponse {
  video_id: string;
  original_filename: string;
  saved_filename: string;
  file_size: number;
  status: UploadStatus;
}

export interface UploadVideoRequest {
  file: File;
}

export interface VideoMetadata {
  duration: number | null;
  width: number | null;
  height: number | null;
  fps: number | null;
  video_codec: string | null;
  audio_present: boolean;
  audio_codec: string | null;
}

export interface PreprocessingResult {
  video_id: string;
  video_path: string;
  metadata: VideoMetadata;
  audio_path: string | null;
  extracted_frame_directory: string;
  frame_timestamps: number[];
  frame_count: number;
  preprocessing_status: string;
  warnings: string[];
  details: Record<string, unknown>;
}

export type PreprocessingState = 'idle' | 'in-progress' | 'complete' | 'failed';
