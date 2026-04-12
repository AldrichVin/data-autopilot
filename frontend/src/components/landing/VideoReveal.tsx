import { useRef, useEffect, useState } from "react";

interface VideoRevealProps {
  src: string;
  progress: number;
}

export default function VideoReveal({ src, progress }: VideoRevealProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [ready, setReady] = useState(false);
  const rafRef = useRef(0);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const onLoaded = () => {
      video.play().then(() => {
        video.pause();
        setReady(true);
      }).catch(() => setReady(true));
    };

    if (video.readyState >= 2) {
      onLoaded();
    } else {
      video.addEventListener("loadeddata", onLoaded, { once: true });
      return () => video.removeEventListener("loadeddata", onLoaded);
    }
  }, [src]);

  useEffect(() => {
    if (!ready) return;
    const video = videoRef.current;
    if (!video?.duration) return;

    cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(() => {
      video.currentTime = progress * video.duration;
    });
  }, [progress, ready]);

  return (
    <video
      ref={videoRef}
      muted
      playsInline
      preload="auto"
      className="h-auto w-full max-w-lg rounded-2xl"
    >
      <source src={src} type="video/mp4" />
    </video>
  );
}
