import type { DataProfile } from "../../types";

interface DataSummaryProps {
  profile: DataProfile;
  filename: string;
}

export default function DataSummary({ profile, filename }: DataSummaryProps) {
  return (
    <div className="rounded-xl bg-white/5 p-6">
      <h2 className="mb-4 text-lg font-semibold text-white">{filename}</h2>
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
            <tr className="border-b border-white/10 text-left text-neutral-400">
              <th className="pb-2 pr-4">Column</th>
              <th className="pb-2 pr-4">Type</th>
              <th className="pb-2 pr-4">Nulls</th>
              <th className="pb-2 pr-4">Unique</th>
              <th className="pb-2">Sample</th>
            </tr>
          </thead>
          <tbody>
            {profile.columns.map((col) => (
              <tr key={col.name} className="border-b border-white/5">
                <td className="py-2 pr-4 font-medium text-white">{col.name}</td>
                <td className="py-2 pr-4">
                  <span
                    className={`rounded px-2 py-0.5 text-xs ${
                      col.inferred_type === "numeric"
                        ? "bg-blue-500/20 text-blue-300"
                        : col.inferred_type === "categorical"
                          ? "bg-purple-500/20 text-purple-300"
                          : col.inferred_type === "datetime"
                            ? "bg-green-500/20 text-green-300"
                            : "bg-white/10 text-neutral-400"
                    }`}
                  >
                    {col.inferred_type}
                  </span>
                </td>
                <td className="py-2 pr-4 text-neutral-400">
                  {col.null_count} ({col.null_pct}%)
                </td>
                <td className="py-2 pr-4 text-neutral-400">{col.unique_count}</td>
                <td className="py-2 text-neutral-500 truncate max-w-xs">
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
    <div className="rounded-lg bg-white/5 p-3 text-center">
      <div className="text-2xl font-bold text-white">{value}</div>
      <div className="text-xs text-neutral-400">{label}</div>
    </div>
  );
}
