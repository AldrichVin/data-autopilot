import { useRef, useEffect } from "react";

interface PlotlyChartProps {
  spec: Record<string, unknown>;
}

export default function PlotlyChart({ spec }: PlotlyChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const renderChart = async () => {
      const Plotly = await import("plotly.js-dist-min");

      const lightLayout = {
        ...(spec.layout as Record<string, unknown> ?? {}),
        paper_bgcolor: "transparent",
        plot_bgcolor: "#ffffff",
        font: { color: "#3a3a3c", family: "'DM Sans', system-ui, sans-serif", size: 12 },
        xaxis: {
          ...((spec.layout as Record<string, unknown>)?.xaxis as Record<string, unknown> ?? {}),
          gridcolor: "#f0f0f0",
          linecolor: "#e5e5ea",
          tickfont: { color: "#636366" },
          titlefont: { color: "#1c1c1e" },
        },
        yaxis: {
          ...((spec.layout as Record<string, unknown>)?.yaxis as Record<string, unknown> ?? {}),
          gridcolor: "#f0f0f0",
          linecolor: "#e5e5ea",
          tickfont: { color: "#636366" },
          titlefont: { color: "#1c1c1e" },
        },
        legend: {
          font: { color: "#636366" },
        },
        margin: { l: 50, r: 20, t: 40, b: 50 },
      };

      const config = {
        displayModeBar: false,
        responsive: true,
      };

      Plotly.default.newPlot(
        containerRef.current!,
        spec.data as Plotly.Data[],
        lightLayout as Partial<Plotly.Layout>,
        config,
      );
    };

    renderChart().catch(console.error);

    return () => {
      if (containerRef.current) {
        import("plotly.js-dist-min").then((Plotly) => {
          Plotly.default.purge(containerRef.current!);
        }).catch(() => {});
      }
    };
  }, [spec]);

  return <div ref={containerRef} className="w-full min-h-[300px] rounded-lg border border-neutral-200" />;
}
