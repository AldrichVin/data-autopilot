interface PreviewTableProps {
  rows: Record<string, unknown>[];
}

export default function PreviewTable({ rows }: PreviewTableProps) {
  if (rows.length === 0) return null;

  const columns = Object.keys(rows[0]);

  return (
    <div className="rounded-xl bg-white/5 p-6">
      <h3 className="mb-4 text-sm font-semibold text-neutral-400">
        Preview (first {rows.length} rows)
      </h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/10 text-left text-neutral-400">
              {columns.map((col) => (
                <th key={col} className="pb-2 pr-4 whitespace-nowrap">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className="border-b border-white/5">
                {columns.map((col) => (
                  <td
                    key={col}
                    className="py-1.5 pr-4 text-neutral-300 whitespace-nowrap"
                  >
                    {String(row[col] ?? "")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
