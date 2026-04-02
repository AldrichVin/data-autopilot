import { motion, useScroll, useTransform } from "framer-motion";
import { Link } from "react-router-dom";

export default function NavBar() {
  const { scrollY } = useScroll();
  const bgOpacity = useTransform(scrollY, [0, 100], [0, 1]);
  const borderOpacity = useTransform(scrollY, [0, 100], [0, 0.08]);

  return (
    <motion.nav
      className="fixed inset-x-0 top-0 z-50 flex h-14 items-center justify-between px-6"
      style={{
        backgroundColor: useTransform(bgOpacity, (v) => `rgba(250,250,250,${v * 0.95})`),
        backdropFilter: useTransform(bgOpacity, (v) => `blur(${v * 16}px)`),
        borderBottom: useTransform(
          borderOpacity,
          (v) => `1px solid rgba(0,0,0,${v})`
        ),
      }}
    >
      <Link
        to="/"
        className="text-xs font-medium tracking-[0.15em] text-neutral-400 uppercase transition hover:text-neutral-900"
      >
        Data Autopilot
      </Link>
      <Link
        to="/app"
        className="border border-neutral-300 px-4 py-1.5 text-xs font-medium text-neutral-600 transition hover:border-neutral-900 hover:text-neutral-900"
      >
        Launch App
      </Link>
    </motion.nav>
  );
}
