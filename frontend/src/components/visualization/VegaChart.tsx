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
        labelColor: "#636366",
        titleColor: "#1c1c1e",
        gridColor: "#f0f0f0",
        domainColor: "#e5e5ea",
      },
      legend: { labelColor: "#636366", titleColor: "#1c1c1e" },
      title: { color: "#1c1c1e" },
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
