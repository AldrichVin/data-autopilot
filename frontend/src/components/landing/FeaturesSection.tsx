import { useRef } from "react";
import { motion, useInView } from "framer-motion";

const FEATURES = [
  {
    number: "01",
    title: "Smart Profiling",
    description:
      "Column types, distributions, anomalies — detected the moment your data lands. No config required.",
  },
  {
    number: "02",
    title: "Dual-Engine Cleaning",
    description:
      "Python or R. Same 6-step pipeline — dedup, type fixes, missing values, outliers, strings, consistency.",
  },
  {
    number: "03",
    title: "Auto Visualizations",
    description:
      "Histograms, scatter plots, time series, heatmaps — picked based on what your columns actually contain.",
  },
  {
    number: "04",
    title: "Tableau Export",
    description:
      "A .twb workbook with .hyper extract, ready to open. Also CSV and PNG bundles.",
  },
];

function FeatureRow({
  number,
  title,
  description,
  index,
}: {
  number: string;
  title: string;
  description: string;
  index: number;
}) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-40px" });

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 16 }}
      animate={isInView ? { opacity: 1, y: 0 } : {}}
      transition={{
        duration: 0.5,
        ease: [0.25, 0.1, 0.25, 1],
        delay: index * 0.06,
      }}
      className="group grid grid-cols-[3rem_1fr] gap-x-6 border-t border-neutral-200 py-8 sm:grid-cols-[3rem_12rem_1fr]"
    >
      <span className="text-sm tabular-nums text-neutral-300">{number}</span>
      <h3 className="text-base font-semibold text-neutral-900">{title}</h3>
      <p className="col-start-2 mt-2 text-sm leading-relaxed text-neutral-400 sm:col-start-3 sm:mt-0">
        {description}
      </p>
    </motion.div>
  );
}

export default function FeaturesSection() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-60px" });

  return (
    <section className="grain relative z-10 overflow-hidden bg-[#fafafa] px-6 py-32">
      <div className="mx-auto max-w-3xl">
        <motion.div
          ref={ref}
          initial={{ opacity: 0, y: 16 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5 }}
          className="mb-16"
        >
          <p className="mb-3 text-xs font-medium tracking-[0.25em] text-neutral-300 uppercase">
            What it does
          </p>
          <h2 className="text-2xl font-bold text-neutral-900 sm:text-3xl">
            Everything your data needs,
            <br />
            <span className="font-serif-accent italic font-normal text-neutral-400">
              nothing it doesn't.
            </span>
          </h2>
        </motion.div>

        <div>
          {FEATURES.map((feature, i) => (
            <FeatureRow key={feature.number} {...feature} index={i} />
          ))}
        </div>
      </div>
    </section>
  );
}
