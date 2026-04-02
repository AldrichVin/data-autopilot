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
        <h1 className="mb-2 text-3xl font-bold text-neutral-900">
          Upload your dataset
        </h1>
        <p className="text-neutral-400">
          Drop a CSV. Get cleaned data, interactive charts, and a Tableau
          workbook — automatically.
        </p>
      </div>

      <div
        {...getRootProps()}
        className={`mb-6 cursor-pointer rounded-lg border-2 border-dashed p-12 text-center transition ${
          isDragActive
            ? "border-neutral-900 bg-neutral-100"
            : file
              ? "border-neutral-900 bg-neutral-50"
              : "border-neutral-300 bg-white hover:border-neutral-400"
        }`}
      >
        <input {...getInputProps()} />
        {file ? (
          <div>
            <p className="text-lg font-medium text-neutral-900">{file.name}</p>
            <p className="mt-1 text-sm text-neutral-400">
              {(file.size / 1024).toFixed(1)} KB — click or drop to replace
            </p>
          </div>
        ) : (
          <div>
            <p className="text-lg text-neutral-500">
              {isDragActive ? "Drop your CSV here" : "Drag & drop a CSV file"}
            </p>
            <p className="mt-1 text-sm text-neutral-400">
              or click to browse (max 50 MB)
            </p>
          </div>
        )}
      </div>

      <div className="mb-6 flex items-center justify-center gap-4">
        <span className="text-sm text-neutral-400">Engine:</span>
        <button
          onClick={() => setEngine("python")}
          className={`rounded-full px-4 py-2 text-sm font-medium transition ${
            engine === "python"
              ? "bg-neutral-900 text-white"
              : "border border-neutral-300 text-neutral-500 hover:border-neutral-900 hover:text-neutral-900"
          }`}
        >
          Python (Pandas)
        </button>
        <button
          onClick={() => setEngine("r")}
          className={`rounded-full px-4 py-2 text-sm font-medium transition ${
            engine === "r"
              ? "bg-neutral-900 text-white"
              : "border border-neutral-300 text-neutral-500 hover:border-neutral-900 hover:text-neutral-900"
          }`}
        >
          R (tidyverse)
        </button>
      </div>

      <div className="text-center">
        <button
          onClick={handleSubmit}
          disabled={!file || isLoading}
          className="rounded-full bg-neutral-900 px-8 py-2.5 text-sm font-semibold text-white transition hover:bg-neutral-700 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {isLoading ? "Processing..." : "Analyze & Clean"}
        </button>
      </div>
    </div>
  );
}
