import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import type { Engine } from "../types";

interface HomePageProps {
  onUpload: (file: File, engine: Engine) => void;
  isLoading: boolean;
}

export default function HomePage({ onUpload, isLoading }: HomePageProps) {
  const [engine, setEngine] = useState<Engine>("python");
  const [file, setFile] = useState<File | null>(null);

  const onDrop = useCallback((accepted: File[]) => {
    if (accepted.length > 0) {
      setFile(accepted[0]);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "text/csv": [".csv"] },
    maxFiles: 1,
    disabled: isLoading,
  });

  const handleSubmit = () => {
    if (file) onUpload(file, engine);
  };

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-8 text-center">
        <h1 className="mb-2 text-4xl font-bold text-white">Data Autopilot</h1>
        <p className="text-neutral-400">
          Drop a CSV. Get cleaned data, interactive charts, and a Tableau
          workbook — automatically.
        </p>
      </div>

      <div
        {...getRootProps()}
        className={`mb-6 cursor-pointer rounded-xl border-2 border-dashed p-12 text-center transition ${
          isDragActive
            ? "border-blue-400 bg-blue-500/10"
            : file
              ? "border-green-500/50 bg-green-500/5"
              : "border-white/20 bg-white/5 hover:border-white/40"
        }`}
      >
        <input {...getInputProps()} />
        {file ? (
          <div>
            <p className="text-lg text-green-400">{file.name}</p>
            <p className="mt-1 text-sm text-neutral-500">
              {(file.size / 1024).toFixed(1)} KB — click or drop to replace
            </p>
          </div>
        ) : (
          <div>
            <p className="text-lg text-neutral-300">
              {isDragActive ? "Drop your CSV here" : "Drag & drop a CSV file"}
            </p>
            <p className="mt-1 text-sm text-neutral-500">
              or click to browse (max 50 MB)
            </p>
          </div>
        )}
      </div>

      <div className="mb-6 flex items-center justify-center gap-4">
        <span className="text-sm text-neutral-400">Engine:</span>
        <button
          onClick={() => setEngine("python")}
          className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
            engine === "python"
              ? "bg-blue-500 text-white"
              : "bg-white/5 text-neutral-400 hover:bg-white/10"
          }`}
        >
          Python (Pandas)
        </button>
        <button
          onClick={() => setEngine("r")}
          className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
            engine === "r"
              ? "bg-blue-500 text-white"
              : "bg-white/5 text-neutral-400 hover:bg-white/10"
          }`}
        >
          R (tidyverse)
        </button>
      </div>

      <div className="text-center">
        <button
          onClick={handleSubmit}
          disabled={!file || isLoading}
          className="rounded-xl bg-blue-500 px-8 py-3 text-lg font-semibold text-white transition hover:bg-blue-600 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {isLoading ? "Processing..." : "Analyze & Clean"}
        </button>
      </div>
    </div>
  );
}
