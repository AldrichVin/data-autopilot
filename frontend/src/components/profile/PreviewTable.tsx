interface PreviewTableProps {
  rows: Record<string, unknown>[];
}

export default function PreviewTable({ rows }: PreviewTableProps) {
  if (rows.length === 0) return null;

  const columns = Object.keys(rows[0]);

  return (
    <div>
      <h3 className="mb-4 text-xs font-semibold uppercase tracking-wide text-neutral-400">
        Preview (first {rows.length} rows)
      </h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b-2 border-neutral-900 text-left">
              {columns.map((col) => (
                <th key={col} className="pb-2 pr-4 text-xs font-semibold uppercase tracking-wide text-neutral-400 whitespace-nowrap">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className="border-b border-neutral-100 hover:bg-neutral-50">
                {columns.map((col) => (
                  <td
                    key={col}
                    className="py-1.5 pr-4 text-neutral-600 whitespace-nowrap"
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
