export interface CaptureSession {
  id: string;
  user_id: string;
  workspace_id: string;
  source_type: string | null;
  source_label: string | null;
  status: string;
  card_count: number;
  confirmed_count: number;
  pending_count: number;
  started_at: string;
  closed_at: string | null;
}

export interface OcrSummary {
  extracted_fields: Record<string, unknown>;
  field_confidences: Record<string, number>;
  overall_confidence?: number | null;
  engine?: string | null;
  engine_version?: string | null;
}

export interface CardListItem {
  id: string;
  status: string;
  review_status: string;
  review_deferred_at: string | null;
  capture_method: string;
  source_label: string | null;
  image_url: string | null;
  created_at: string;
  version?: number;
  ocr_summary: OcrSummary | null;
}

export interface CardDetail extends CardListItem {
  capture_session_id: string | null;
  version: number;
  source_type: string | null;
  ocr_result: OcrSummary | null;
}

export interface DuplicateWarning {
  previous_card_id: string;
  scanned_at: string;
  message: string;
}

export interface RawCardUploadResponse {
  raw_card_id: string;
  status: string;
  capture_session_id: string | null;
  duplicate_warning?: DuplicateWarning | null;
}

export interface ImportCardResponse {
  raw_card_id: string;
  status: string;
  review_status: string;
  capture_method: string;
  message: string;
  extracted_preview?: {
    name?: string | null;
    company?: string | null;
    title?: string | null;
  } | null;
}

export type ThumbnailStatus = "uploading" | "queued" | "ocr_processing" | "ocr_done" | "ocr_failed" | "upload_failed";

export interface CaptureThumbnail {
  id: string;
  localUrl: string;
  status: ThumbnailStatus;
  cardId?: string;
}
