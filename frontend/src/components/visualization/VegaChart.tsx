import { useRef, useEffect } from "react";
import vegaEmbed from "vega-embed";

interface VegaChartProps {
  spec: Record<string, unknown>;
}

export default function VegaChart({ spec }: VegaChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);

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

  useEffect(() => {
    if (!containerRef.current) return;
    const result = vegaEmbed(containerRef.current, themedSpec as never, {
      actions: false,
      renderer: "svg",
    });
    return () => {
      result.then((r) => r.finalize()).catch(() => {});
    };
  }, [spec]);

  return <div ref={containerRef} className="overflow-x-auto" />;
}
