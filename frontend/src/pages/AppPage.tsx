import { useState } from "react";
import { cleanData, uploadFile, visualize } from "../api/client";
import Header from "../components/common/Header";
import StepIndicator from "../components/common/StepIndicator";
import HomePage from "./HomePage";
import ResultsPage from "./ResultsPage";
import type {
  AppStatus,
  CleanResponse,
  Engine,
  UploadResponse,
  VisualizeResponse,
} from "../types";

export default function AppPage() {
  const [status, setStatus] = useState<AppStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null);
  const [cleanResult, setCleanResult] = useState<CleanResponse | null>(null);
  const [vizResult, setVizResult] = useState<VisualizeResponse | null>(null);

  const handleUpload = async (file: File, engine: Engine) => {
    setError(null);
    try {
      setStatus("uploading");
      const upload = await uploadFile(file);
      setUploadResult(upload);
      setStatus("profiled");

      setStatus("cleaning");
      const cleaned = await cleanData(upload.session_id, engine);
      setCleanResult(cleaned);
      setStatus("cleaned");

      setStatus("visualizing");
      const viz = await visualize(upload.session_id);
      setVizResult(viz);
      setStatus("complete");
    } catch (err: unknown) {
      setStatus("error");
      const message =
        err instanceof Error ? err.message : "Something went wrong";
      setError(message);
    }
  };

  const handleReset = () => {
    setStatus("idle");
    setError(null);
    setUploadResult(null);
    setCleanResult(null);
    setVizResult(null);
  };

  const showResults =
    status !== "idle" && status !== "uploading" && uploadResult;

  return (
    <div className="min-h-screen bg-[#fafafa]">
      <Header onReset={handleReset} />
      <main className="mx-auto max-w-5xl px-6 py-8">
        <StepIndicator status={status} />

        {error && (
          <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {error}
          </div>
        )}

        {!showResults && (
          <HomePage onUpload={handleUpload} isLoading={status === "uploading"} />
        )}

        {showResults && (
          <ResultsPage
            status={status}
            upload={uploadResult}
            clean={cleanResult}
            viz={vizResult}
          />
        )}
      </main>
    </div>
  );
}
