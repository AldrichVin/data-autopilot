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
    <div>
      <h2 className="mb-4 text-lg font-semibold text-neutral-900">Downloads</h2>

      {/* Reports */}
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-neutral-400">
        Reports
      </h3>
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <DownloadCard
          title="HTML Report"
          description="Self-contained interactive report with charts, alerts, and findings"
          href={getExportUrl(sessionId, "report_html")}
          primary
        />
        <DownloadCard
          title="PDF Report"
          description="Print-ready professional report document"
          href={getExportUrl(sessionId, "report_pdf")}
          primary
        />
      </div>

      {/* Data & Assets */}
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-neutral-400">
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
  primary,
}: {
  title: string;
  description: string;
  href: string;
  primary?: boolean;
}) {
  return (
    <a
      href={href}
      download
      className={`block rounded-lg border p-4 transition hover:bg-neutral-50 ${
        primary
          ? "border-neutral-900"
          : "border-neutral-200"
      }`}
    >
      <div className="font-medium text-neutral-900">{title}</div>
      <div className="mt-1 text-xs text-neutral-400">{description}</div>
    </a>
  );
}
