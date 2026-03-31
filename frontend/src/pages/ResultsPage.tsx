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
      <div className="mb-6 flex gap-2 border-b border-white/10 pb-2">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => t.ready && setTab(t.key)}
            disabled={!t.ready}
            className={`rounded-t-lg px-4 py-2 text-sm font-medium transition ${
              tab === t.key
                ? "bg-white/10 text-white"
                : t.ready
                  ? "text-neutral-400 hover:text-white"
                  : "cursor-not-allowed text-neutral-600"
            }`}
          >
            {t.label}
            {!t.ready && status !== "complete" && status !== "error" && (
              <span className="ml-2 text-xs text-blue-400">...</span>
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
              className={`rounded px-3 py-1 text-sm ${vizMode === "vegalite" ? "bg-blue-500 text-white" : "bg-white/5 text-neutral-400"}`}
            >
              Interactive (Vega-Lite)
            </button>
            <button
              onClick={() => setVizMode("matplotlib")}
              className={`rounded px-3 py-1 text-sm ${vizMode === "matplotlib" ? "bg-blue-500 text-white" : "bg-white/5 text-neutral-400"}`}
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
