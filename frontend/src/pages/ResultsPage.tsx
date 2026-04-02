import { useState } from "react";
import CleaningReportView from "../components/cleaning/CleaningReport";
import DataSummary from "../components/profile/DataSummary";
import PreviewTable from "../components/profile/PreviewTable";
import ChartGrid from "../components/visualization/ChartGrid";
import TableauDownload from "../components/visualization/TableauDownload";
import type {
  AppStatus,
  CleanResponse,
  UploadResponse,
  VisualizeResponse,
  VizMode,
} from "../types";

interface ResultsPageProps {
  status: AppStatus;
  upload: UploadResponse;
  clean: CleanResponse | null;
  viz: VisualizeResponse | null;
}

type Tab = "profile" | "cleaning" | "charts" | "downloads";

export default function ResultsPage({
  status,
  upload,
  clean,
  viz,
}: ResultsPageProps) {
  const [tab, setTab] = useState<Tab>("profile");
  const [vizMode, setVizMode] = useState<VizMode>("vegalite");

  const tabs: { key: Tab; label: string; ready: boolean }[] = [
    { key: "profile", label: "Data Profile", ready: true },
    { key: "cleaning", label: "Cleaning Report", ready: !!clean },
    { key: "charts", label: "Visualizations", ready: !!viz },
    { key: "downloads", label: "Downloads", ready: !!viz },
  ];

  return (
    <div>
      <div className="mb-6 flex gap-1 border-b border-neutral-200 pb-0">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => t.ready && setTab(t.key)}
            disabled={!t.ready}
            className={`px-4 py-2.5 text-sm font-medium transition ${
              tab === t.key
                ? "border-b-2 border-neutral-900 text-neutral-900"
                : t.ready
                  ? "text-neutral-400 hover:text-neutral-900"
                  : "cursor-not-allowed text-neutral-300"
            }`}
          >
            {t.label}
            {!t.ready && status !== "complete" && status !== "error" && (
              <span className="ml-2 text-xs text-neutral-400">...</span>
            )}
          </button>
        ))}
      </div>

      {tab === "profile" && (
        <div className="space-y-6">
          <DataSummary profile={upload.profile} filename={upload.filename} />
          <PreviewTable rows={upload.preview} />
        </div>
      )}

      {tab === "cleaning" && clean && (
        <CleaningReportView report={clean.cleaning_report} engine={clean.engine_used} />
      )}

      {tab === "charts" && viz && (
        <div className="space-y-4">
          <div className="flex items-center gap-4">
            <span className="text-sm text-neutral-400">View as:</span>
            <button
              onClick={() => setVizMode("vegalite")}
              className={`rounded-full px-3 py-1 text-sm font-medium transition ${
                vizMode === "vegalite"
                  ? "bg-neutral-900 text-white"
                  : "border border-neutral-300 text-neutral-500 hover:border-neutral-900"
              }`}
            >
              Interactive (Vega-Lite)
            </button>
            <button
              onClick={() => setVizMode("matplotlib")}
              className={`rounded-full px-3 py-1 text-sm font-medium transition ${
                vizMode === "matplotlib"
                  ? "bg-neutral-900 text-white"
                  : "border border-neutral-300 text-neutral-500 hover:border-neutral-900"
              }`}
            >
              Static (Matplotlib)
            </button>
          </div>
          <ChartGrid
            charts={viz.charts}
            mode={vizMode}
            sessionId={viz.session_id}
          />
        </div>
      )}

      {tab === "downloads" && viz && (
        <TableauDownload sessionId={viz.session_id} tableauUrl={viz.tableau_download_url} />
      )}
    </div>
  );
}
