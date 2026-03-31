import axios from "axios";
import type {
  CleanResponse,
  Engine,
  UploadResponse,
  VisualizeResponse,
} from "../types";

const API_BASE = import.meta.env.VITE_API_URL || "";

const api = axios.create({ baseURL: API_BASE });

export async function uploadFile(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await api.post<UploadResponse>("/api/v1/upload", formData);
  return data;
}

export async function cleanData(
  sessionId: string,
  engine: Engine
): Promise<CleanResponse> {
  const { data } = await api.post<CleanResponse>("/api/v1/clean", {
    session_id: sessionId,
    engine,
  });
  return data;
}

export async function visualize(
  sessionId: string,
  formats: string[] = ["vegalite", "matplotlib", "tableau"]
): Promise<VisualizeResponse> {
  const { data } = await api.post<VisualizeResponse>("/api/v1/visualize", {
    session_id: sessionId,
    formats,
  });
  return data;
}

export function getExportUrl(sessionId: string, format: string): string {
  return `${API_BASE}/api/v1/export/${sessionId}/${format}`;
}

export function getMatplotlibUrl(
  sessionId: string,
  chartId: string
): string {
  return `${API_BASE}/api/v1/matplotlib/${sessionId}/${chartId}.png`;
}
