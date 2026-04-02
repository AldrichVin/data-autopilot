import type { DataProfile } from "../../types";

interface DataSummaryProps {
  profile: DataProfile;
  filename: string;
}

export default function DataSummary({ profile, filename }: DataSummaryProps) {
  return (
    <div>
      <h2 className="mb-4 text-lg font-semibold text-neutral-900">{filename}</h2>
      <div className="mb-6 grid grid-cols-4 gap-4">
        <Stat label="Rows" value={profile.total_rows.toLocaleString()} />
        <Stat label="Columns" value={profile.total_columns.toString()} />
        <Stat label="Duplicates" value={profile.duplicate_row_count.toString()} />
        <Stat
          label="Numeric"
          value={profile.columns.filter((c) => c.inferred_type === "numeric").length.toString()}
        />
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b-2 border-neutral-900 text-left">
              <th className="pb-2 pr-4 text-xs font-semibold uppercase tracking-wide text-neutral-400">Column</th>
              <th className="pb-2 pr-4 text-xs font-semibold uppercase tracking-wide text-neutral-400">Type</th>
              <th className="pb-2 pr-4 text-xs font-semibold uppercase tracking-wide text-neutral-400">Nulls</th>
              <th className="pb-2 pr-4 text-xs font-semibold uppercase tracking-wide text-neutral-400">Unique</th>
              <th className="pb-2 text-xs font-semibold uppercase tracking-wide text-neutral-400">Sample</th>
            </tr>
          </thead>
          <tbody>
            {profile.columns.map((col) => (
              <tr key={col.name} className="border-b border-neutral-100 hover:bg-neutral-50">
                <td className="py-2 pr-4 font-medium text-neutral-900">{col.name}</td>
                <td className="py-2 pr-4">
                  <span
                    className={`rounded px-2 py-0.5 text-xs font-medium ${
                      col.inferred_type === "numeric"
                        ? "bg-blue-50 text-blue-700"
                        : col.inferred_type === "categorical"
                          ? "bg-purple-50 text-purple-700"
                          : col.inferred_type === "datetime"
                            ? "bg-green-50 text-green-700"
                            : "bg-neutral-100 text-neutral-500"
                    }`}
                  >
                    {col.inferred_type}
                  </span>
                </td>
                <td className="py-2 pr-4 text-neutral-500">
                  {col.null_count} ({col.null_pct}%)
                </td>
                <td className="py-2 pr-4 text-neutral-500">{col.unique_count}</td>
                <td className="py-2 text-neutral-400 truncate max-w-xs">
                  {col.sample_values.join(", ")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-t-2 border-neutral-900 pt-3">
      <div className="text-2xl font-light text-neutral-900">{value}</div>
      <div className="text-xs font-medium uppercase tracking-wide text-neutral-400">{label}</div>
    </div>
  );
}
