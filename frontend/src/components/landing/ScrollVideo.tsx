import { useRef, useEffect, useState } from "react";
import { useScroll, useMotionValueEvent } from "framer-motion";

interface ScrollVideoProps {
  src: string;
  poster?: string;
  containerRef: React.RefObject<HTMLElement | null>;
}

export default function ScrollVideo({
  src,
  poster,
  containerRef,
}: ScrollVideoProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [loaded, setLoaded] = useState(false);
  const rafRef = useRef<number>(0);

  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start start", "end end"],
  });

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleLoaded = () => {
      video
        .play()
        .then(() => {
          video.pause();
          setLoaded(true);
        })
        .catch(() => {
          setLoaded(true);
        });
    };

    if (video.readyState >= 2) {
      handleLoaded();
    } else {
      video.addEventListener("loadeddata", handleLoaded, { once: true });
      return () => video.removeEventListener("loadeddata", handleLoaded);
    }
  }, [src]);

  useMotionValueEvent(scrollYProgress, "change", (v) => {
    if (!loaded || !videoRef.current) return;
    cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(() => {
      const video = videoRef.current;
      if (video && video.duration) {
        video.currentTime = v * video.duration;
      }
    });
  });

  return (
    <div className="fixed inset-0 z-0">
      <video
        ref={videoRef}
        muted
        playsInline
        preload="auto"
        poster={poster}
        className="h-full w-full object-cover"
      >
        <source src={src} type="video/mp4" />
      </video>
      {/* Slight wash for text readability over white video */}
      <div className="absolute inset-0 bg-white/30" />
    </div>
  );
}
