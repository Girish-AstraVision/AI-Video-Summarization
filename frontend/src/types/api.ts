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

export interface DetectionRecord {
  frame_number: number;
  frame_filename: string;
  timestamp: number;
  label: string;
  confidence: number;
  bounding_box: [number, number, number, number];
}

export interface VisualDetectionResult {
  video_id: string;
  frames_processed: number;
  number_of_detections: number;
  detections: DetectionRecord[];
  processing_time: number;
  model_name: string;
}

export interface ModerationEvent {
  video_id: string;
  timestamp: number;
  start_time: number;
  end_time: number;
  category: string;
  severity: string;
  confidence: number;
  text: string;
  message: string;
}

export interface ModerationResult {
  video_id: string;
  total_events: number;
  moderation_events: ModerationEvent[];
}

export interface ChapterKeyFrame {
  frame_filename: string;
  timestamp: number;
  importance_score: number;
}

export interface ImportantObject {
  label: string;
  confidence: number;
}

export interface ChapterItem {
  chapter_number: number;
  start_time: number;
  end_time: number;
  title: string;
  summary: string;
  key_frames: ChapterKeyFrame[];
  important_objects: ImportantObject[];
}

export interface ChapterResponse {
  video_id: string;
  number_of_chapters: number;
  chapters: ChapterItem[];
  processing_time: number;
}

export interface SelectedFrame {
  frame_filename: string;
  timestamp: number;
  importance_score: number;
  detected_objects: string[];
}

export interface KeyFrameSelectionResult {
  video_id: string;
  total_frames_analyzed: number;
  selected_frames: SelectedFrame[];
  number_selected: number;
  processing_time: number;
}

export interface SpeechSegment {
  segment_number: number;
  start: number;
  end: number;
  text: string;
}

export interface SpeechToTextResult {
  video_id: string;
  audio_path: string;
  model_name: string;
  detected_language: string;
  language_probability: number;
  number_of_segments: number;
  segments: SpeechSegment[];
  processing_time: number;
}

export type PreprocessingState = 'idle' | 'in-progress' | 'complete' | 'failed';
