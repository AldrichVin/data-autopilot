interface HeaderProps {
  onReset: () => void;
}

export default function Header({ onReset }: HeaderProps) {
  return (
    <header className="border-b border-white/10 bg-[#0a0a0a]">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4">
        <button onClick={onReset} className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-blue-500 flex items-center justify-center text-white font-bold text-sm">
            DA
          </div>
          <span className="text-lg font-semibold text-white">
            Data Autopilot
          </span>
        </button>
        <a
          href="https://github.com/AldrichVin/data-autopilot"
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-neutral-400 hover:text-white transition"
        >
          GitHub
        </a>
      </div>
    </header>
  );
}
