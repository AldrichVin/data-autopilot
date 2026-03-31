import type { CleaningReport } from "../../types";

interface CleaningReportProps {
  report: CleaningReport;
  engine: string;
}

export default function CleaningReportView({
  report,
  engine,
}: CleaningReportProps) {
  return (
    <div className="rounded-xl bg-white/5 p-6">
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">Cleaning Report</h2>
        <div className="flex items-center gap-4 text-sm text-neutral-400">
          <span>
            Engine: <span className="text-white">{engine}</span>
          </span>
          <span>
            Duration: <span className="text-white">{report.duration_ms}ms</span>
          </span>
        </div>
      </div>

      <div className="mb-6 grid grid-cols-2 gap-4">
        <div className="rounded-lg bg-white/5 p-4">
          <div className="text-sm text-neutral-400">Before</div>
          <div className="text-xl font-bold text-white">
            {report.original_shape[0].toLocaleString()} rows x{" "}
            {report.original_shape[1]} cols
          </div>
        </div>
        <div className="rounded-lg bg-white/5 p-4">
          <div className="text-sm text-neutral-400">After</div>
          <div className="text-xl font-bold text-green-400">
            {report.cleaned_shape[0].toLocaleString()} rows x{" "}
            {report.cleaned_shape[1]} cols
          </div>
        </div>
      </div>

      <div className="space-y-3">
        {report.steps.map((step, i) => (
          <div
            key={i}
            className="flex items-start gap-3 rounded-lg bg-white/5 p-4"
          >
            <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-500/20 text-xs font-bold text-blue-400">
              {i + 1}
            </div>
            <div>
              <div className="font-medium text-white">{step.step.replace(/_/g, " ")}</div>
              <div className="text-sm text-neutral-400">{step.description}</div>
              {step.rows_affected > 0 && (
                <div className="mt-1 text-xs text-neutral-500">
                  {step.rows_affected} values affected
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
