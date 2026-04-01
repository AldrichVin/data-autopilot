import { getExportUrl } from "../../api/client";

interface TableauDownloadProps {
  sessionId: string;
  tableauUrl?: string | null;
}

export default function TableauDownload({
  sessionId,
  tableauUrl,
}: TableauDownloadProps) {
  return (
    <div className="rounded-xl bg-white/5 p-6">
      <h2 className="mb-4 text-lg font-semibold text-white">Downloads</h2>

      {/* Reports */}
      <h3 className="mb-3 text-sm font-medium uppercase tracking-wide text-neutral-400">
        Reports
      </h3>
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <DownloadCard
          title="HTML Report"
          description="Self-contained interactive report with charts, alerts, and findings"
          href={getExportUrl(sessionId, "report_html")}
          accent="blue"
        />
        <DownloadCard
          title="PDF Report"
          description="Print-ready professional report document"
          href={getExportUrl(sessionId, "report_pdf")}
          accent="blue"
        />
      </div>

      {/* Data & Assets */}
      <h3 className="mb-3 text-sm font-medium uppercase tracking-wide text-neutral-400">
        Data &amp; Assets
      </h3>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <DownloadCard
          title="Cleaned CSV"
          description="Download the cleaned dataset"
          href={getExportUrl(sessionId, "cleaned_csv")}
        />
        <DownloadCard
          title="All Charts (PNG)"
          description="ZIP of all Matplotlib charts"
          href={getExportUrl(sessionId, "charts")}
        />
        {tableauUrl && (
          <DownloadCard
            title="Tableau Workbook"
            description=".twb + .hyper extract — open in Tableau Desktop"
            href={getExportUrl(sessionId, "tableau")}
          />
        )}
      </div>
    </div>
  );
}

function DownloadCard({
  title,
  description,
  href,
  accent,
}: {
  title: string;
  description: string;
  href: string;
  accent?: string;
}) {
  const borderClass =
    accent === "blue"
      ? "border border-blue-500/30 hover:border-blue-500/60"
      : "border border-transparent";

  return (
    <a
      href={href}
      download
      className={`block rounded-lg bg-white/5 p-4 transition hover:bg-white/10 ${borderClass}`}
    >
      <div className="font-medium text-white">{title}</div>
      <div className="mt-1 text-xs text-neutral-400">{description}</div>
    </a>
  );
}
