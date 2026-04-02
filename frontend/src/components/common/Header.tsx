import { Link } from "react-router-dom";

interface HeaderProps {
  onReset: () => void;
}

export default function Header({ onReset }: HeaderProps) {
  return (
    <header className="border-b border-neutral-200 bg-[#fafafa]">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
        <button onClick={onReset} className="flex items-center gap-2">
          <span className="text-xs font-medium tracking-[0.15em] text-neutral-400 uppercase transition hover:text-neutral-900">
            Data Autopilot
          </span>
        </button>
        <Link
          to="/"
          className="border border-neutral-300 px-4 py-1.5 text-xs font-medium text-neutral-600 transition hover:border-neutral-900 hover:text-neutral-900"
        >
          Home
        </Link>
      </div>
    </header>
  );
}
