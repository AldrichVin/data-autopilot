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
}: {
  title: string;
  description: string;
  href: string;
}) {
  return (
    <a
      href={href}
      download
      className="block rounded-lg bg-white/5 p-4 transition hover:bg-white/10"
    >
      <div className="font-medium text-white">{title}</div>
      <div className="mt-1 text-xs text-neutral-400">{description}</div>
    </a>
  );
}
