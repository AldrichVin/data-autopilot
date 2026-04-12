import { useRef } from "react";
import { motion, useScroll, useTransform } from "framer-motion";

interface TextPhase {
  title: string;
  subtitle?: string;
  startProgress: number;
  endProgress: number;
}

interface ScrollSectionProps {
  height: string;
  textPhases: TextPhase[];
  align?: "left" | "center";
  media?: React.ReactNode;
}

export default function ScrollSection({
  height,
  textPhases,
  align = "left",
  media,
}: ScrollSectionProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start start", "end end"],
  });

  return (
    <div ref={containerRef} className="relative" style={{ height }}>
      <div className="sticky top-0 z-10 flex h-screen items-center justify-center overflow-hidden">
        {media ? (
          <div className="flex h-full w-full flex-col items-center justify-center gap-8 px-6 lg:flex-row lg:gap-12 lg:px-20">
            <div className="relative flex-1">
              {textPhases.map((phase) => (
                <PhaseText
                  key={phase.title}
                  phase={phase}
                  scrollYProgress={scrollYProgress}
                  align={align}
                />
              ))}
            </div>
            <div className="flex flex-1 items-center justify-center">
              {media}
            </div>
          </div>
        ) : (
          textPhases.map((phase) => (
            <PhaseText
              key={phase.title}
              phase={phase}
              scrollYProgress={scrollYProgress}
              align={align}
            />
          ))
        )}
      </div>
    </div>
  );
}

function PhaseText({
  phase,
  scrollYProgress,
  align,
}: {
  phase: TextPhase;
  scrollYProgress: ReturnType<typeof useScroll>["scrollYProgress"];
  align: "left" | "center";
}) {
  const fadeIn = phase.startProgress;
  const hold = phase.startProgress + (phase.endProgress - phase.startProgress) * 0.2;
  const holdEnd = phase.endProgress - (phase.endProgress - phase.startProgress) * 0.2;
  const fadeOut = phase.endProgress;

  const opacity = useTransform(
    scrollYProgress,
    [fadeIn, hold, holdEnd, fadeOut],
    [0, 1, 1, 0]
  );

  const y = useTransform(
    scrollYProgress,
    [fadeIn, hold, holdEnd, fadeOut],
    [24, 0, 0, -24]
  );

  return (
    <motion.div
      style={{ opacity, y }}
      className={`absolute inset-0 z-10 flex flex-col justify-center px-6 sm:px-12 lg:px-20 ${
        align === "center" ? "items-center text-center" : "items-start text-left"
      }`}
    >
      <h3 className="max-w-2xl text-2xl font-semibold text-neutral-900 sm:text-3xl lg:text-4xl">
        {phase.title}
      </h3>
      {phase.subtitle && (
        <p className="mt-4 max-w-md text-sm leading-relaxed text-neutral-400">
          {phase.subtitle}
        </p>
      )}
    </motion.div>
  );
}
