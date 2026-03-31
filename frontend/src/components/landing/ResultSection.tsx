import ScrollSection from "./ScrollSection";

const TEXT_PHASES = [
  {
    title: "Interactive charts, generated automatically",
    subtitle:
      "Vega-Lite charts you can hover, zoom, and explore — plus static Matplotlib exports.",
    startProgress: 0,
    endProgress: 0.45,
  },
  {
    title: "Export anywhere",
    subtitle:
      "Download cleaned CSV, PNG chart bundles, or a ready-to-open Tableau workbook with .hyper extract.",
    startProgress: 0.5,
    endProgress: 0.95,
  },
];

export default function ResultSection() {
  return (
    <ScrollSection height="150vh" textPhases={TEXT_PHASES} align="center" />
  );
}
