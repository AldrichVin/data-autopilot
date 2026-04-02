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

      const darkLayout = {
        ...(spec.layout as Record<string, unknown> ?? {}),
        paper_bgcolor: "transparent",
        plot_bgcolor: "transparent",
        font: { color: "#a3a3a3", family: "Inter, sans-serif" },
        xaxis: {
          ...((spec.layout as Record<string, unknown>)?.xaxis as Record<string, unknown> ?? {}),
          gridcolor: "#262626",
          linecolor: "#404040",
          tickfont: { color: "#a3a3a3" },
          titlefont: { color: "#e5e5e5" },
        },
        yaxis: {
          ...((spec.layout as Record<string, unknown>)?.yaxis as Record<string, unknown> ?? {}),
          gridcolor: "#262626",
          linecolor: "#404040",
          tickfont: { color: "#a3a3a3" },
          titlefont: { color: "#e5e5e5" },
        },
        legend: {
          font: { color: "#a3a3a3" },
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
        darkLayout as Partial<Plotly.Layout>,
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

  return <div ref={containerRef} className="w-full min-h-[300px]" />;
}
