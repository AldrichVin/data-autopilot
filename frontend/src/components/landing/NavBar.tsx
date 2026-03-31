import { motion, useScroll, useTransform } from "framer-motion";
import { Link } from "react-router-dom";

export default function NavBar() {
  const { scrollY } = useScroll();
  const bgOpacity = useTransform(scrollY, [0, 100], [0, 1]);
  const borderOpacity = useTransform(scrollY, [0, 100], [0, 0.06]);

  return (
    <motion.nav
      className="fixed inset-x-0 top-0 z-50 flex h-14 items-center justify-between px-6"
      style={{
        backgroundColor: useTransform(bgOpacity, (v) => `rgba(10,10,10,${v * 0.92})`),
        backdropFilter: useTransform(bgOpacity, (v) => `blur(${v * 16}px)`),
        borderBottom: useTransform(
          borderOpacity,
          (v) => `1px solid rgba(255,255,255,${v})`
        ),
      }}
    >
      <Link
        to="/"
        className="text-xs font-medium tracking-[0.15em] text-neutral-400 uppercase transition hover:text-white"
      >
        Data Autopilot
      </Link>
      <Link
        to="/app"
        className="border border-neutral-700 px-4 py-1.5 text-xs font-medium text-neutral-300 transition hover:border-neutral-500 hover:text-white"
      >
        Launch App
      </Link>
    </motion.nav>
  );
}
