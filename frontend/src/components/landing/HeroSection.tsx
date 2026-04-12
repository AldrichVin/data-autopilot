import { motion } from "framer-motion";
import { Link } from "react-router-dom";

export default function HeroSection() {
  return (
    <div className="relative">
      <div className="grain h-screen overflow-hidden bg-[#fafafa]">
        <div className="relative z-10 flex h-full flex-col justify-center px-6 sm:px-12 lg:pl-20">
          <div className="max-w-lg">
            <motion.p
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.1 }}
              className="mb-6 text-xs font-medium tracking-[0.25em] text-neutral-400 uppercase"
            >
              Data Autopilot
            </motion.p>

            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.25 }}
              className="text-5xl font-bold leading-[1.08] tracking-tight text-neutral-900 sm:text-6xl lg:text-7xl"
            >
              From raw CSV
              <br />
              to{" "}
              <span className="font-serif-accent italic font-normal text-neutral-500">
                clean insights
              </span>
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.45 }}
              className="mt-6 max-w-md text-base leading-relaxed text-neutral-400"
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
                className="rounded-full bg-neutral-900 px-7 py-2.5 text-sm font-semibold text-white transition hover:bg-neutral-700"
              >
                Get Started
              </Link>
              <a
                href="#problem"
                className="text-sm font-medium text-neutral-400 underline decoration-neutral-300 underline-offset-4 transition hover:text-neutral-900 hover:decoration-neutral-500"
              >
                See how it works
              </a>
            </motion.div>
          </div>
        </div>
      </div>
    </div>
  );
}
