import { useRef } from "react";
import { motion, useScroll, useTransform } from "framer-motion";
import { Link } from "react-router-dom";

export default function HeroSection() {
  const ref = useRef(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start start", "end start"],
  });
  const opacity = useTransform(scrollYProgress, [0, 0.5], [1, 0]);
  const y = useTransform(scrollYProgress, [0, 0.5], [0, -80]);

  return (
    <section
      ref={ref}
      className="grain relative z-10 flex min-h-screen items-center justify-center overflow-hidden bg-[#0a0a0a]"
    >
      {/* Single warm accent glow — asymmetric, not centered */}
      <div className="pointer-events-none absolute -right-32 top-1/4 h-[500px] w-[350px] rotate-12 rounded-full bg-amber-500/[0.04] blur-[140px]" />

      <motion.div
        style={{ opacity, y }}
        className="relative z-10 mx-auto max-w-3xl px-6"
      >
        <motion.p
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="mb-6 text-xs font-medium tracking-[0.25em] text-neutral-500 uppercase"
        >
          Data Autopilot
        </motion.p>

        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.25 }}
          className="text-5xl font-bold leading-[1.08] tracking-tight text-white sm:text-6xl lg:text-7xl"
        >
          From raw CSV
          <br />
          to{" "}
          <span className="font-serif-accent italic font-normal text-amber-200/90">
            clean insights
          </span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.45 }}
          className="mt-6 max-w-md text-base leading-relaxed text-neutral-500"
        >
          Upload a dataset. Get automated cleaning, interactive charts, and
          Tableau-ready exports — in seconds.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.65 }}
          className="mt-10 flex items-center gap-5"
        >
          <Link
            to="/app"
            className="rounded-full bg-white px-7 py-2.5 text-sm font-semibold text-neutral-900 transition hover:bg-neutral-100"
          >
            Get Started
          </Link>
          <a
            href="#problem"
            className="text-sm font-medium text-neutral-400 underline decoration-neutral-700 underline-offset-4 transition hover:text-white hover:decoration-neutral-400"
          >
            See how it works
          </a>
        </motion.div>
      </motion.div>

      {/* Scroll indicator */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 0.4 }}
        transition={{ delay: 1.4, duration: 0.8 }}
        className="absolute bottom-12 left-1/2 -translate-x-1/2"
      >
        <motion.div
          animate={{ y: [0, 6, 0] }}
          transition={{ duration: 2.2, repeat: Infinity, ease: "easeInOut" }}
          className="text-xs tracking-widest text-neutral-600"
        >
          scroll
        </motion.div>
      </motion.div>
    </section>
  );
}
