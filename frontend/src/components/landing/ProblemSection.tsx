import ScrollSection from "./ScrollSection";

const TEXT_PHASES = [
  {
    title: "Your data arrives messy",
    subtitle:
      "Missing values, inconsistent types, duplicate rows — every CSV has problems hiding in plain sight.",
    startProgress: 0,
    endProgress: 0.45,
  },
  {
    title: "Manual cleaning takes hours",
    subtitle:
      "Writing one-off scripts, fixing edge cases, re-running pipelines. It's tedious work that shouldn't be manual.",
    startProgress: 0.5,
    endProgress: 0.95,
  },
];

export default function ProblemSection() {
  return (
    <section id="problem">
      <ScrollSection height="150vh" textPhases={TEXT_PHASES} />
    </section>
  );
}
