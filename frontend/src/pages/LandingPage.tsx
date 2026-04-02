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
    <div className="min-h-screen bg-[#fafafa]">
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

      <footer className="relative z-10 border-t border-neutral-200 bg-[#fafafa] px-6 py-8">
        <div className="mx-auto flex max-w-4xl items-center justify-between">
          <span className="text-xs text-neutral-300">
            Data Autopilot — built by{" "}
            <a
              href="https://github.com/AldrichVin"
              target="_blank"
              rel="noopener noreferrer"
              className="text-neutral-400 transition hover:text-neutral-900"
            >
              Aldrich Vincent
            </a>
          </span>
          <a
            href="https://github.com/AldrichVin/data-autopilot"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-neutral-300 transition hover:text-neutral-900"
          >
            GitHub
          </a>
        </div>
      </footer>
    </div>
  );
}
