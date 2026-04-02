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
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-neutral-900">Cleaning Report</h2>
        <div className="flex items-center gap-4 text-sm text-neutral-400">
          <span>
            Engine: <span className="font-medium text-neutral-900">{engine}</span>
          </span>
          <span>
            Duration: <span className="font-medium text-neutral-900">{report.duration_ms}ms</span>
          </span>
        </div>
      </div>

      <div className="mb-6 grid grid-cols-2 gap-4">
        <div className="border-t-2 border-neutral-900 pt-3">
          <div className="text-xs font-medium uppercase tracking-wide text-neutral-400">Before</div>
          <div className="text-xl font-light text-neutral-900">
            {report.original_shape[0].toLocaleString()} rows &times;{" "}
            {report.original_shape[1]} cols
          </div>
        </div>
        <div className="border-t-2 border-neutral-900 pt-3">
          <div className="text-xs font-medium uppercase tracking-wide text-neutral-400">After</div>
          <div className="text-xl font-light text-neutral-900">
            {report.cleaned_shape[0].toLocaleString()} rows &times;{" "}
            {report.cleaned_shape[1]} cols
          </div>
        </div>
      </div>

      <div className="space-y-0">
        {report.steps.map((step, i) => (
          <div
            key={i}
            className="flex items-start gap-3 border-b border-neutral-100 py-4"
          >
            <div className="flex-shrink-0 text-sm font-semibold text-neutral-400">
              {i + 1}
            </div>
            <div>
              <div className="font-medium text-neutral-900 capitalize">{step.step.replace(/_/g, " ")}</div>
              <div className="text-sm text-neutral-500">{step.description}</div>
              {step.rows_affected > 0 && (
                <div className="mt-1 text-xs font-medium text-neutral-400">
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
