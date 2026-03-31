interface StaticChartProps {
  url: string;
  alt: string;
}

export default function StaticChart({ url, alt }: StaticChartProps) {
  return (
    <img
      src={url}
      alt={alt}
      className="w-full rounded-lg"
      loading="lazy"
    />
  );
}
