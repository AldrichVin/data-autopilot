import ScrollSection from "./ScrollSection";

const TEXT_PHASES = [
  {
    title: "Upload",
    subtitle: "Drag and drop any CSV. Column types and statistics are profiled instantly.",
    startProgress: 0,
    endProgress: 0.3,
  },
  {
    title: "Clean",
    subtitle:
      "A 6-step pipeline: deduplication, type fixing, missing values, outliers, string normalization, consistency checks.",
    startProgress: 0.33,
    endProgress: 0.63,
  },
  {
    title: "Visualize",
    subtitle:
      "Charts are auto-selected based on your data: histograms, scatter plots, time series, heatmaps.",
    startProgress: 0.66,
    endProgress: 0.95,
  },
];

export default function ProcessSection() {
  return (
    <ScrollSection height="200vh" textPhases={TEXT_PHASES} align="center" />
  );
}
