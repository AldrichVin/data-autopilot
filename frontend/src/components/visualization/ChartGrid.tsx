import { lazy, Suspense } from "react";
import type { ChartSpec, VizMode } from "../../types";
import StaticChart from "./StaticChart";
import VegaChart from "./VegaChart";

const PlotlyChart = lazy(() => import("./PlotlyChart"));

interface ChartGridProps {
  charts: ChartSpec[];
  mode: VizMode;
  sessionId: string;
}

export default function ChartGrid({ charts, mode, sessionId }: ChartGridProps) {
  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
      {charts.map((chart) => (
        <div
          key={chart.chart_id}
          className="rounded-xl bg-white/5 p-4"
        >
          <h3 className="mb-2 text-sm font-semibold text-white">
            {chart.title}
          </h3>
          <p className="mb-3 text-xs text-neutral-500">{chart.description}</p>

          {chart.plotly_spec ? (
            <Suspense
              fallback={
                <div className="flex h-48 items-center justify-center text-neutral-500">
                  Loading chart...
                </div>
              }
            >
              <PlotlyChart spec={chart.plotly_spec} />
            </Suspense>
          ) : mode === "vegalite" && chart.vegalite_spec ? (
            <VegaChart spec={chart.vegalite_spec} />
          ) : chart.matplotlib_url ? (
            <StaticChart url={chart.matplotlib_url} alt={chart.title} />
          ) : (
            <div className="flex h-48 items-center justify-center text-neutral-500">
              Chart not available in this mode
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
