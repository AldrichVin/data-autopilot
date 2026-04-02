import type { AppStatus } from "../../types";

interface StepIndicatorProps {
  status: AppStatus;
}

const STEPS = [
  { key: "upload", label: "Upload", activeIn: ["uploading", "profiled"] },
  { key: "clean", label: "Clean", activeIn: ["cleaning", "cleaned"] },
  { key: "visualize", label: "Visualize", activeIn: ["visualizing", "complete"] },
] as const;

export default function StepIndicator({ status }: StepIndicatorProps) {
  if (status === "idle") return null;

  const getStepStatus = (step: (typeof STEPS)[number]) => {
    const allStatuses: AppStatus[] = [
      "uploading",
      "profiled",
      "cleaning",
      "cleaned",
      "visualizing",
      "complete",
    ];
    const currentIdx = allStatuses.indexOf(status);
    const stepStart = allStatuses.indexOf(step.activeIn[0] as AppStatus);
    const stepEnd = allStatuses.indexOf(
      step.activeIn[step.activeIn.length - 1] as AppStatus
    );

    if (currentIdx > stepEnd) return "done";
    if (currentIdx >= stepStart && currentIdx <= stepEnd) return "active";
    return "pending";
  };

  return (
    <div className="mb-8 flex items-center justify-center gap-2">
      {STEPS.map((step, i) => {
        const s = getStepStatus(step);
        return (
          <div key={step.key} className="flex items-center gap-2">
            <div
              className={`flex h-8 items-center gap-2 rounded-full px-4 text-sm font-medium transition ${
                s === "done"
                  ? "bg-neutral-900 text-white"
                  : s === "active"
                    ? "border border-neutral-900 text-neutral-900"
                    : "bg-neutral-100 text-neutral-400"
              }`}
            >
              {s === "done" ? "\u2713" : s === "active" ? "..." : " "}
              <span className="ml-1">{step.label}</span>
            </div>
            {i < STEPS.length - 1 && (
              <div className="h-px w-8 bg-neutral-300" />
            )}
          </div>
        );
      })}
    </div>
  );
}
