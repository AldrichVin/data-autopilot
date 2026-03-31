import { useRef } from "react";
import NavBar from "../components/landing/NavBar";
import HeroSection from "../components/landing/HeroSection";
import ScrollVideo from "../components/landing/ScrollVideo";
import ProblemSection from "../components/landing/ProblemSection";
import ProcessSection from "../components/landing/ProcessSection";
import ResultSection from "../components/landing/ResultSection";
import FeaturesSection from "../components/landing/FeaturesSection";
import CTASection from "../components/landing/CTASection";

const VIDEO_SRC = "/videos/hero.mp4";

export default function LandingPage() {
  const videoContainerRef = useRef<HTMLDivElement>(null);

  return (
    <div className="min-h-screen bg-[#0a0a0a]">
      <NavBar />
      <HeroSection />

      {/* Single video spans all scroll sections */}
      <div ref={videoContainerRef}>
        <ScrollVideo src={VIDEO_SRC} containerRef={videoContainerRef} />
        <ProblemSection />
        <ProcessSection />
        <ResultSection />
      </div>

      <FeaturesSection />
      <CTASection />

      <footer className="relative z-10 border-t border-neutral-800/50 bg-[#0a0a0a] px-6 py-8">
        <div className="mx-auto flex max-w-4xl items-center justify-between">
          <span className="text-xs text-neutral-600">
            Data Autopilot — built by{" "}
            <a
              href="https://github.com/AldrichVin"
              target="_blank"
              rel="noopener noreferrer"
              className="text-neutral-500 transition hover:text-white"
            >
              Aldrich Vincent
            </a>
          </span>
          <a
            href="https://github.com/AldrichVin/data-autopilot"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-neutral-600 transition hover:text-white"
          >
            GitHub
          </a>
        </div>
      </footer>
    </div>
  );
}
