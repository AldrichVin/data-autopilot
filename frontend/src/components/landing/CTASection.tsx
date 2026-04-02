import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { Link } from "react-router-dom";

export default function CTASection() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-80px" });

  return (
    <section className="grain relative z-10 flex min-h-[60vh] items-center justify-center overflow-hidden bg-[#fafafa] px-6">
      <motion.div
        ref={ref}
        initial={{ opacity: 0, y: 20 }}
        animate={isInView ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 0.7 }}
        className="relative z-10 max-w-xl"
      >
        <h2 className="text-3xl font-bold text-neutral-900 sm:text-4xl">
          Ready to autopilot
          <br />
          <span className="font-serif-accent italic font-normal text-neutral-400">
            your data?
          </span>
        </h2>
        <p className="mt-4 text-sm text-neutral-400">
          No sign-up. No API key. Just upload and go.
        </p>
        <Link
          to="/app"
          className="mt-8 inline-block rounded-full bg-neutral-900 px-8 py-3 text-sm font-semibold text-white transition hover:bg-neutral-700"
        >
          Launch App
        </Link>
      </motion.div>
    </section>
  );
}
