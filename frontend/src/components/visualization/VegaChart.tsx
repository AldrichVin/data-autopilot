import { VegaLite } from "react-vega";

interface VegaChartProps {
  spec: Record<string, unknown>;
}

export default function VegaChart({ spec }: VegaChartProps) {
  const themedSpec = {
    ...spec,
    background: "transparent",
    config: {
      axis: {
        labelColor: "#a3a3a3",
        titleColor: "#e5e5e5",
        gridColor: "#262626",
        domainColor: "#404040",
      },
      legend: { labelColor: "#a3a3a3", titleColor: "#e5e5e5" },
      title: { color: "#e5e5e5" },
      view: { stroke: "transparent" },
    },
  };

  return (
    <div className="overflow-x-auto">
      <VegaLite spec={themedSpec as never} actions={false} />
    </div>
  );
}
