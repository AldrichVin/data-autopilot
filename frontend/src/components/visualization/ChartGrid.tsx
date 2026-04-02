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

export default function ChartGrid({ charts, mode, sessionId: _sessionId }: ChartGridProps) {
  return (
    <div className="grid grid-cols-1 gap-8 md:grid-cols-2">
      {charts.map((chart) => (
        <div
          key={chart.chart_id}
          className="overflow-hidden"
        >
          <h3 className="mb-1 text-sm font-semibold text-neutral-900">
            {chart.title}
          </h3>
          <p className="mb-3 text-xs text-neutral-400">{chart.description}</p>

          {chart.plotly_spec ? (
            <Suspense
              fallback={
                <div className="flex h-48 items-center justify-center text-neutral-400">
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
            <div className="flex h-48 items-center justify-center text-neutral-400">
              Chart not available in this mode
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
