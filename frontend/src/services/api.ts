import { API_BASE_URL } from '../config/env';
import type {
  ApiHealthResponse,
  ChapterResponse,
  KeyFrameSelectionResult,
  ModerationResult,
  PreprocessingResult,
  SpeechToTextResult,
  SummarizeVideoRequest,
  SummarizeVideoResponse,
  UploadVideoResponse,
  VisualDetectionResult,
} from '../types/api';

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...((options.headers as Record<string, string> | undefined) ?? {}),
    },
    ...options,
  });

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

async function parseUploadError(response: Response): Promise<string> {
  const defaultMessage = 'The upload request failed. Please try again.';

  if (response.status === 400) {
    return 'The selected file is invalid. Please upload a supported video file.';
  }

  if (response.status === 413) {
    return 'The uploaded file is too large for this frontend check. Please choose a video under 500 MB.';
  }

  if (response.status === 500) {
    return 'The backend encountered a server error while processing the upload. Please try again.';
  }

  try {
    const data = (await response.json()) as { detail?: unknown; message?: unknown };
    const detail = data.detail ?? data.message;
    if (typeof detail === 'string' && detail.trim().length > 0) {
      return detail;
    }
  } catch {
    // Ignore JSON parsing failure and fall back to a generic message.
  }

  return defaultMessage;
}

export async function uploadVideo(file: File): Promise<UploadVideoResponse> {
  const formData = new FormData();
  formData.append('file', file);

  try {
    const response = await fetch(`${API_BASE_URL}/api/videos/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(await parseUploadError(response));
    }

    return (await response.json()) as UploadVideoResponse;
  } catch (error) {
    if (error instanceof Error) {
      const message = error.message.trim();
      if (message.length > 0) {
        throw new Error(message);
      }
    }

    throw new Error('The backend is unavailable or unreachable. Please check the server and try again.');
  }
}

export async function preprocessVideo(videoId: string): Promise<PreprocessingResult> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/videos/${encodeURIComponent(videoId)}/preprocess`, {
      method: 'POST',
    });

    if (!response.ok) {
      if (response.status === 404) {
        throw new Error(`Video "${videoId}" was not found. Please upload it again.`);
      }

      if (response.status === 400) {
        throw new Error('The preprocessing request is invalid for this video.');
      }

      if (response.status === 500) {
        throw new Error('The backend encountered an error while preprocessing the video.');
      }

      throw new Error(`Preprocessing failed with status ${response.status}. Please try again.`);
    }

    return (await response.json()) as PreprocessingResult;
  } catch (error) {
    if (error instanceof Error && error.message) {
      throw new Error(error.message);
    }

    throw new Error('A network error occurred while trying to preprocess the video.');
  }
}

export async function detectVisualObjects(videoId: string, confidenceThreshold = 0.5): Promise<VisualDetectionResult> {
  const threshold = Number.isFinite(confidenceThreshold) ? confidenceThreshold : 0.5;
  const queryParams = new URLSearchParams({ confidence_threshold: String(threshold) });

  try {
    const response = await fetch(`${API_BASE_URL}/api/videos/${encodeURIComponent(videoId)}/detect?${queryParams.toString()}`, {
      method: 'POST',
    });

    if (!response.ok) {
      if (response.status === 404) {
        throw new Error(`Video "${videoId}" was not found. Please upload it again.`);
      }

      if (response.status === 400) {
        throw new Error('The RT-DETR detection request is invalid for this video or threshold.');
      }

      if (response.status === 500) {
        throw new Error('The backend encountered an error while running RT-DETR visual analysis.');
      }

      throw new Error(`Visual detection failed with status ${response.status}. Please try again.`);
    }

    return (await response.json()) as VisualDetectionResult;
  } catch (error) {
    if (error instanceof Error && error.message) {
      throw new Error(error.message);
    }

    throw new Error('A network error occurred while running RT-DETR visual analysis.');
  }
}

export async function transcribeVideo(videoId: string): Promise<SpeechToTextResult> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/videos/${encodeURIComponent(videoId)}/transcribe`, {
      method: 'POST',
    });

    if (!response.ok) {
      if (response.status === 404) {
        throw new Error(`Video "${videoId}" was not found. Please upload it again.`);
      }

      if (response.status === 400) {
        throw new Error('The speech transcription request is invalid for this video.');
      }

      if (response.status === 500) {
        throw new Error('The backend encountered an error while running Whisper speech analysis.');
      }

      throw new Error(`Speech transcription failed with status ${response.status}. Please try again.`);
    }

    return (await response.json()) as SpeechToTextResult;
  } catch (error) {
    if (error instanceof Error && error.message) {
      throw new Error(error.message);
    }

    throw new Error('A network error occurred while running Whisper speech analysis.');
  }
}

export async function moderateVideo(videoId: string): Promise<ModerationResult> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/videos/${encodeURIComponent(videoId)}/moderate`, {
      method: 'POST',
    });

    if (!response.ok) {
      if (response.status === 404) {
        throw new Error(`Video "${videoId}" was not found. Please upload it again.`);
      }

      if (response.status === 400) {
        throw new Error('The moderation request is invalid for this video.');
      }

      if (response.status === 500) {
        throw new Error('The backend encountered an error while running content moderation.');
      }

      throw new Error(`Moderation failed with status ${response.status}. Please try again.`);
    }

    return (await response.json()) as ModerationResult;
  } catch (error) {
    if (error instanceof Error && error.message) {
      throw new Error(error.message);
    }

    throw new Error('A network error occurred while running content moderation.');
  }
}

export async function generateChapters(videoId: string, maxChapters = 5): Promise<ChapterResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/videos/${encodeURIComponent(videoId)}/chapters`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ max_chapters: maxChapters }),
    });

    if (!response.ok) {
      if (response.status === 404) {
        throw new Error(`Video "${videoId}" was not found. Please upload it again.`);
      }

      if (response.status === 400) {
        throw new Error('The chapter-generation request is invalid for this video or chapter count.');
      }

      if (response.status === 500) {
        throw new Error('The backend encountered an error while generating chapters.');
      }

      throw new Error(`Chapter generation failed with status ${response.status}. Please try again.`);
    }

    return (await response.json()) as ChapterResponse;
  } catch (error) {
    if (error instanceof Error && error.message) {
      throw new Error(error.message);
    }

    throw new Error('A network error occurred while generating chapters.');
  }
}

export async function getKeyFrames(videoId: string, numKeyframes = 5): Promise<KeyFrameSelectionResult> {
  try {
    const queryParams = new URLSearchParams({ num_keyframes: String(numKeyframes) });
    const response = await fetch(`${API_BASE_URL}/api/videos/${encodeURIComponent(videoId)}/keyframes?${queryParams.toString()}`, {
      method: 'POST',
    });

    if (!response.ok) {
      if (response.status === 404) {
        throw new Error(`Video "${videoId}" was not found. Please upload it again.`);
      }

      if (response.status === 400) {
        throw new Error('The key-frame request is invalid for this video or frame count.');
      }

      if (response.status === 500) {
        throw new Error('The backend encountered an error while selecting key frames.');
      }

      throw new Error(`Key-frame selection failed with status ${response.status}. Please try again.`);
    }

    return (await response.json()) as KeyFrameSelectionResult;
  } catch (error) {
    if (error instanceof Error && error.message) {
      throw new Error(error.message);
    }

    throw new Error('A network error occurred while selecting key frames.');
  }
}

export async function summarizeVideo(
  videoId: string,
  summaryLength: 'short' | 'medium' | 'long' = 'medium',
  targetDuration?: number,
): Promise<SummarizeVideoResponse> {
  const body: SummarizeVideoRequest = {
    summary_length: summaryLength,
    ...(typeof targetDuration === 'number' ? { target_duration: targetDuration } : {}),
  };

  try {
    const response = await fetch(`${API_BASE_URL}/api/videos/${encodeURIComponent(videoId)}/summarize`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      if (response.status === 404) {
        throw new Error(`Video "${videoId}" was not found. Please upload it again.`);
      }

      if (response.status === 400) {
        throw new Error('The summary request is invalid for this video, summary length, or target duration.');
      }

      if (response.status === 500) {
        throw new Error('The backend encountered an error while generating the summary.');
      }

      throw new Error(`Summary generation failed with status ${response.status}. Please try again.`);
    }

    return (await response.json()) as SummarizeVideoResponse;
  } catch (error) {
    if (error instanceof Error && error.message) {
      throw new Error(error.message);
    }

    throw new Error('A network error occurred while generating the summary.');
  }
}

export const api = {
  getHealth: () => request<ApiHealthResponse>('/'),
  get: <T>(endpoint: string) => request<T>(endpoint),
  post: <T>(endpoint: string, body: unknown) =>
    request<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
};

export { API_BASE_URL };
